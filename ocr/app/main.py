from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import sys

import httpx

from app.config import logger, settings
from app.pipeline import process_doc


def main() -> None:
    """Ponto de entrada do pipeline.

    Descobre arquivos suportados no diretório alvo, distribui o processamento
    entre threads e exibe um sumário de sucessos e falhas ao final.
    """
    if not settings.docs_dir.is_dir():
        logger.critical("Diretório '{}' não encontrado — abortando", settings.docs_dir.resolve())
        sys.exit(1)

    all_files = [f for f in settings.docs_dir.iterdir() if f.suffix.lower() in settings.supported_extensions]
    if not all_files:
        logger.warning('Nenhum arquivo suportado encontrado em {}', settings.docs_dir)
        sys.exit(0)

    max_workers = max(1, (os.cpu_count() or 4))
    logger.info('{} arquivo(s) encontrado(s) — {} thread(s) alocada(s)', len(all_files), max_workers)

    succeeded = 0
    failed = 0

    with (
        httpx.Client(timeout=120.0, headers={'X-Service-Key': settings.internal_service_key}) as client,
        ThreadPoolExecutor(max_workers=max_workers) as executor,
    ):
        futures = {executor.submit(process_doc, f, client): f for f in all_files}

        for future in as_completed(futures):
            try:
                future.result()
                succeeded += 1
            except Exception:  # noqa: BLE001
                failed += 1

    logger.info('Pipeline concluído — {} sucesso(s), {} falha(s)', succeeded, failed)


if __name__ == '__main__':
    main()
