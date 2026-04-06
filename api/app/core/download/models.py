from dataclasses import dataclass
from enum import StrEnum


class DownloadState(StrEnum):
    """
    Define os estados finitos do Singleton.

    Transições válidas:
    IDLE -> DOWNLOADING
    DOWNLOADING -> COMPLETED | ERROR
    COMPLETED | ERROR -> DOWNLOADING (via nova requisição)
    """

    IDLE = 'IDLE'
    DOWNLOADING = 'DOWNLOADING'
    COMPLETED = 'COMPLETED'
    ERROR = 'ERROR'


@dataclass(frozen=True)
class DownloadStatus:
    state: DownloadState
    total: int
    downloaded: int
    error: str | None = None
