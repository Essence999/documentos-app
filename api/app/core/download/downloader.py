from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import aiohttp
import anyio
import anyio.abc
from anyio.streams.memory import MemoryObjectReceiveStream
from litestar import Litestar, status_codes

from app.common.exceptions import AuthExpiredError
from app.config.app import AppState
from app.config.base import downloader_settings
from app.core.download.models import DownloadState, DownloadStatus
from app.core.download.state_manager import DownloadStateManager
from app.core.log import logger


class DocumentDownloader:
    """
    Gerencia o ciclo de vida do download em lote de documentos PDF.

    Singleton instanciado no lifespan da aplicação. Utiliza um TaskGroup
    externo para executar downloads em background, sobrevivendo ao ciclo
    de vida das requisições HTTP.

    O progresso e o estado são delegados ao DownloadStateManager.
    """

    def __init__(self, task_group: anyio.abc.TaskGroup) -> None:
        self._tg = task_group
        self.save_dir = downloader_settings.save_dir
        self.max_concurrency = downloader_settings.max_concurrency

        self.state_manager = DownloadStateManager()

    async def get_status(self) -> DownloadStatus:
        return await self.state_manager.get_snapshot()

    async def get_pending_ids(self, all_ids: list[str]) -> list[str]:
        """
        Retorna IDs cujos arquivos ainda não foram baixados.

        Remove arquivos .tmp residuais de execuções anteriores.
        Cria o diretório de destino se não existir.
        """
        await self.save_dir.mkdir(parents=True, exist_ok=True)

        existing_files = set()
        async for f in self.save_dir.iterdir():
            if not await f.is_file():
                continue

            if f.suffix == '.tmp':
                await f.unlink()
            else:
                existing_files.add(f.stem)

        return [doc_id for doc_id in all_ids if doc_id not in existing_files]

    async def _worker(self, receive_stream: MemoryObjectReceiveStream[str], session: aiohttp.ClientSession) -> None:
        """Consome IDs do stream e baixa cada documento. Encerra quando o stream fechar."""
        async with receive_stream:
            async for doc_id in receive_stream:
                await self._download_document(doc_id, session)

    async def _download_document(self, doc_id: str, session: aiohttp.ClientSession) -> None:
        """
        Baixa um único documento via HTTP e salva em disco atomicamente (tmp → final).

        Levanta AuthExpiredError se detectar redirecionamento 302.
        Remove o arquivo .tmp em caso de qualquer falha.
        """
        url = f'http://127.0.0.1:8000/documents/{doc_id}/pdf'
        tmp_path = self.save_dir / f'{doc_id}.pdf.tmp'
        final_path = self.save_dir / f'{doc_id}.pdf'

        try:
            async with session.get(url, allow_redirects=False) as response:
                if response.status == status_codes.HTTP_302_FOUND:
                    logger.warning('Redirecionamento detectado para o documento {}: {}', doc_id, response.status)
                    raise AuthExpiredError()

                response.raise_for_status()

                async with await anyio.open_file(tmp_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(64 * 1024):
                        await f.write(chunk)

            await tmp_path.rename(final_path)
            await self.state_manager.increment()

        except BaseException:
            with anyio.CancelScope(shield=True):
                await tmp_path.unlink(missing_ok=True)
            raise

    async def _setup_download_state(self, all_ids: list[str]) -> list[str] | None:
        """
        Prepara o estado para um novo lote.

        Retorna:
            []   — nenhum documento pendente (todos já baixados).
            None — já há um download em andamento, requisição ignorada.
            list — IDs pendentes, estado transicionado para DOWNLOADING.
        """
        pending_ids = await self.get_pending_ids(all_ids)
        if not pending_ids:
            return []

        acquired = await self.state_manager.try_acquire_run(total_docs=len(pending_ids))
        if not acquired:
            return None

        return pending_ids

    async def _execute_concurrent_downloads(self, pending_ids: list[str], cookies: dict[str, str]) -> None:
        """
        Executa os downloads com concorrência limitada por max_concurrency.

        Usa um memory stream como fila de trabalho distribuída entre workers.
        """
        timeout = aiohttp.ClientTimeout(total=300, connect=10)
        async with aiohttp.ClientSession(cookies=cookies, timeout=timeout) as session:
            buffer_size = max(1, len(pending_ids))
            n_workers = min(self.max_concurrency, len(pending_ids))

            send_stream, receive_stream = anyio.create_memory_object_stream[str](max_buffer_size=buffer_size)
            async with anyio.create_task_group() as tg, receive_stream:
                for _ in range(n_workers):
                    tg.start_soon(self._worker, receive_stream.clone(), session)

                async with send_stream:
                    for doc_id in pending_ids:
                        await send_stream.send(doc_id)

    async def _run(self, pending_ids: list[str], cookies: dict[str, str]) -> None:
        """
        Ponto de entrada da task agendada no TaskGroup do lifespan.

        Executa os downloads e garante que o estado final seja sempre
        atualizado — COMPLETED ou ERROR — independente do tipo de falha.
        """
        final_state: tuple[DownloadState, str] | None = None
        try:
            await self._execute_concurrent_downloads(pending_ids, cookies)
            await self.state_manager.finish(DownloadState.COMPLETED)
            return
        except* AuthExpiredError:
            final_state = (DownloadState.ERROR, 'Autenticação expirada')
        except* (aiohttp.ClientError, OSError) as eg:
            final_state = final_state or (DownloadState.ERROR, f'Rede/IO: {eg.exceptions[0]!s}')
        except* Exception as eg:  # noqa: BLE001
            final_state = final_state or (DownloadState.ERROR, f'Interno: {eg.exceptions[0]!s}')

        logger.error(final_state[1])
        await self.state_manager.finish(state=final_state[0], error=final_state[1])

    async def try_schedule(self, all_ids: list[str], cookies: dict[str, str]) -> bool:
        """
        Tenta agendar um lote de downloads no TaskGroup.

        Retorna False se já houver um download em andamento.
        Retorna True se o lote foi agendado ou se não havia pendências.
        """
        pending_ids = await self._setup_download_state(all_ids)
        if pending_ids is None:
            return False
        if not pending_ids:
            await self.state_manager.finish(DownloadState.COMPLETED)
            return True
        self._tg.start_soon(self._run, pending_ids, cookies)
        return True


def provide_downloader(state: AppState) -> DocumentDownloader:
    return state.downloader


@asynccontextmanager
async def downloader_lifespan(app: Litestar) -> AsyncGenerator[None]:
    save_dir = downloader_settings.save_dir
    await save_dir.mkdir(parents=True, exist_ok=True)

    async for tmp in save_dir.glob('*.tmp'):
        await tmp.unlink(missing_ok=True)

    async with anyio.create_task_group() as tg:
        app.state.downloader = DocumentDownloader(task_group=tg)
        yield
        tg.cancel_scope.cancel()
