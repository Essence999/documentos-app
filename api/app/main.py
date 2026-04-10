from litestar import Litestar, Response, get
from litestar.config.cors import CORSConfig
from litestar.di import Provide

from app.api.controller import document_router
from app.api.mock_controller import mock_router
from app.config.app import AppState
from app.core.download import downloader_lifespan
from app.core.download.downloader import provide_downloader


@get('/favicon.ico', sync_to_thread=True)
def favicon() -> Response:
    return Response(content=b'', status_code=204)


app = Litestar(
    debug=True,
    cors_config=CORSConfig(allow_origins=['http://127.0.0.1:4200']),
    dependencies={'downloader': Provide(provide_downloader, sync_to_thread=False, use_cache=True)},
    route_handlers=[mock_router, document_router, favicon],
    lifespan=[downloader_lifespan],
    state=AppState(),
)
