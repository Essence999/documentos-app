import secrets

import anyio
import anyio.to_thread
from litestar import Request, Response, Router, get, patch, status_codes
from litestar.di import Provide

from app.api.repository import DocumentRepositoryMock
from app.api.schemas import ExtractionResultPayload, ExtractionResultStatus
from app.api.service import DocumentService
from app.core.download import DocumentDownloader, DownloadStatus


@get('/download')
async def trigger_download(
    downloader: DocumentDownloader, request: Request, document_service: DocumentService
) -> Response[dict[str, str]]:
    docs = await anyio.to_thread.run_sync(document_service.get_documents)
    ids = [doc.id_to_str for doc in docs]

    scheduled = await downloader.try_schedule(ids, request.cookies)
    if not scheduled:
        return Response({'message': 'already running'}, status_code=status_codes.HTTP_409_CONFLICT)
    return Response({'message': 'accepted'}, status_code=status_codes.HTTP_202_ACCEPTED)


@get('/status')
async def check_status(downloader: DocumentDownloader) -> DownloadStatus:
    return await downloader.get_status()


@get('/{doc_id:str}/pdf')
async def get_document_pdf(doc_id: str, document_service: DocumentService) -> Response[bytes]:
    await anyio.sleep(secrets.randbelow(5))  # Simula latência de acesso ao arquivo
    pdf_content = document_service.get_document_pdf_by_id(doc_id)
    return Response(content=pdf_content, media_type='application/pdf')


@patch('/{doc_id:str}/extraction-result', status_code=204)
async def receive_extraction_result(
    doc_id: str,
    data: ExtractionResultPayload,
    document_service: DocumentService,
) -> None:
    if data.extracted_text:
        await document_service.save_extracted_text(doc_id, data.extracted_text)

    await document_service.delete_document_pdf_by_id(doc_id)

    status = ExtractionResultStatus.SUCCESS if data.extracted_text else ExtractionResultStatus.ERROR
    await document_service.mark_document(doc_id, status)


def provide_document_service() -> DocumentService:
    repository = DocumentRepositoryMock()
    return DocumentService(repository)


document_router = Router(
    path='/documents',
    route_handlers=[
        trigger_download,
        check_status,
        get_document_pdf,
        receive_extraction_result,
    ],
    dependencies={
        'document_service': Provide(provide_document_service, sync_to_thread=False, use_cache=True),
    },
)
