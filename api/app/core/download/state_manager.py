import anyio

from app.core.download.models import DownloadState, DownloadStatus


class DownloadStateManager:
    """
    Máquina de estados para o ciclo de download.

    Todas as mutações e leituras são protegidas por Lock para evitar
    dirty reads e condições de corrida entre workers concorrentes.

    Transições válidas:
        IDLE → DOWNLOADING
        DOWNLOADING → COMPLETED | ERROR
        COMPLETED | ERROR → DOWNLOADING (nova requisição)
    """

    def __init__(self) -> None:
        self._lock = anyio.Lock()
        self._state = DownloadState.IDLE
        self._total = 0
        self._downloaded = 0
        self._error: str | None = None

    async def get_snapshot(self) -> DownloadStatus:
        """Retorna uma cópia imutável do estado atual."""
        async with self._lock:
            return DownloadStatus(state=self._state, total=self._total, downloaded=self._downloaded, error=self._error)

    async def try_acquire_run(self, total_docs: int) -> bool:
        """
        Tenta iniciar um novo download, transicionando para DOWNLOADING.

        Retorna False sem modificar o estado se já estiver em DOWNLOADING.
        Reinicia contadores de progresso e erro a cada nova aquisição.
        """
        async with self._lock:
            if self._state == DownloadState.DOWNLOADING:
                return False
            self._state = DownloadState.DOWNLOADING
            self._error = None
            self._total = total_docs
            self._downloaded = 0
            return True

    async def increment(self) -> None:
        """Incrementa atomicamente o contador de documentos baixados com sucesso."""
        async with self._lock:
            self._downloaded += 1

    async def finish(self, state: DownloadState, error: str | None = None) -> None:
        """Finaliza o lote, transicionando para COMPLETED ou ERROR."""
        async with self._lock:
            self._state = state
            self._error = error
