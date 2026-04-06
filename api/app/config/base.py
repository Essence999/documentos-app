from dataclasses import dataclass
import os

import anyio


@dataclass(frozen=True)
class DownloaderConfig:
    save_dir: anyio.Path
    max_concurrency: int


downloader_settings = DownloaderConfig(
    save_dir=anyio.Path(os.getenv('DOWNLOAD_DIR', 'documents')),
    max_concurrency=int(os.getenv('DOWNLOAD_CONCURRENCY', '100')),
)
