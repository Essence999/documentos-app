from typing import TYPE_CHECKING

from litestar.datastructures import State

if TYPE_CHECKING:
    from app.core.download import DocumentDownloader


class AppState(State):
    downloader: DocumentDownloader
