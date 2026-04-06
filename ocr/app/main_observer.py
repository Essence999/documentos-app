from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path
import signal
import sys
import threading

import httpx
from watchdog.events import (
    DirMovedEvent,
    FileMovedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from app.config import logger, settings
from app.pipeline import process_doc


# ========================= WATCHDOG ==========================================
class DocumentEventHandler(FileSystemEventHandler):
    """Reage à criação de novos arquivos no diretório de documentos.

    Arquivos com extensão não suportada (incluindo .tmp) são silenciosamente
    ignorados. Cada arquivo detectado é submetido ao pool de threads.
    """

    def __init__(self, executor: ThreadPoolExecutor, client: httpx.Client, stop_event: threading.Event) -> None:
        self._executor = executor
        self._client = client
        self._stop_event = stop_event

    def _submit_file(self, path: Path) -> None:
        if path.suffix.lower() not in settings.supported_extensions:
            return

        self._executor.submit(process_doc, path, self._client)

    def on_moved(self, event: FileMovedEvent | DirMovedEvent) -> None:
        if event.is_directory:
            return

        if not isinstance(event.dest_path, str):
            return

        path = Path(event.dest_path)
        self._submit_file(path)


# ========================= STARTUP SCAN ======================================
def startup_scan(executor: ThreadPoolExecutor, client: httpx.Client, stop_event: threading.Event) -> None:
    """Processa arquivos que já existiam no diretório antes do serviço iniciar.

    Cobre o cenário de restart no meio de um processamento: o arquivo permanece
    na pasta (a deleção é responsabilidade da API) e é reprocessado aqui.

    Args:
        executor: Pool de threads para submissão dos jobs.
        client:   Cliente HTTP compartilhado.
        stop_event: Evento para sinalizar o encerramento do serviço.
    """
    existing = [f for f in settings.docs_dir.iterdir() if f.suffix.lower() in settings.supported_extensions]

    if not existing:
        logger.info('Scan de startup: nenhum arquivo pendente')
        return

    logger.info(f'Scan de startup: {len(existing)} arquivo(s) encontrado(s)')

    succeeded = 0
    failed = 0

    futures = {executor.submit(process_doc, f, client): f for f in existing}
    for future in as_completed(futures):
        if stop_event.is_set():
            logger.info('Scan de startup interrompido — cancelando e aguardando threads ativas...')
            break
        try:
            future.result()
            succeeded += 1
        except Exception:  # noqa: BLE001
            failed += 1

    logger.info(f'Scan de startup concluído — {succeeded} sucesso(s), {failed} falha(s)')


# ========================= ENTRYPOINT ========================================
def main() -> None:
    """Ponto de entrada do serviço OCR.

    Executa o scan de startup para processar arquivos pendentes e inicia o
    watchdog para reagir a novos arquivos. Bloqueia até receber SIGTERM ou
    SIGINT, encerrando o observer e aguardando as threads ativas.
    """
    if not settings.docs_dir.is_dir():
        logger.critical(f"Diretório '{settings.docs_dir.resolve()}' não encontrado — abortando")
        sys.exit(1)

    max_workers = max(1, (os.cpu_count() or 4) // 2)
    logger.info(f'Iniciando serviço OCR — {max_workers} thread(s) alocada(s)')

    # Evento usado para bloquear a thread principal até sinal de encerramento
    stop_event = threading.Event()

    def handle_signal(sig: int, _frame: object) -> None:
        logger.warning(f'Sinal {sig} recebido — abortando o processo imediatamente...')
        os._exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    with (
        httpx.Client(timeout=120.0, headers={'X-Service-Key': settings.internal_service_key}) as client,
        ThreadPoolExecutor(max_workers=max_workers) as executor,
    ):
        # 1. Processa arquivos que já estavam na pasta antes de subir
        startup_scan(executor, client, stop_event)

        # 2. Inicia o watchdog para reagir a novos arquivos
        handler = DocumentEventHandler(executor, client, stop_event)
        observer = Observer()
        observer.schedule(handler, path=str(settings.docs_dir), recursive=False)
        observer.start()
        logger.info(f'Watchdog ativo em {settings.docs_dir} — aguardando arquivos...')

        try:
            stop_event.wait()  # bloqueia até SIGTERM/SIGINT
        finally:
            observer.stop()
            observer.join()
            logger.info('Observer encerrado — aguardando threads finalizarem...')
        # O `with ThreadPoolExecutor` aguarda todas as threads ao sair

    logger.info('Serviço OCR encerrado.')


if __name__ == '__main__':
    main()
