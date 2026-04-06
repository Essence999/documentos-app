from anyio import Path

from app import logger
from app.api.repository import DocumentRepositoryMock
from app.api.schemas import DocumentRecord, ExtractionResultStatus


class DocumentService:
    def __init__(self, document_repository: DocumentRepositoryMock) -> None:
        self._repo = document_repository

    def count_documents(self) -> int:
        return self._repo.count_documents()

    def get_documents(self) -> list[DocumentRecord]:
        return self._repo.get_documents()

    def get_document_pdf_by_id(self, doc_id: str) -> bytes:
        return self._repo.get_document_pdf_by_id(doc_id)

    @staticmethod
    async def mark_document(doc_id: str, extraction_status: ExtractionResultStatus) -> None:
        logger.info(f'Marcando documento {doc_id} como {extraction_status}')

    @staticmethod
    async def delete_document_pdf_by_id(doc_id: str) -> None:
        pdf_path = Path('documents') / f'{doc_id}.pdf'
        await pdf_path.unlink(missing_ok=True)

    @staticmethod
    async def save_extracted_text(doc_id: str, extracted_text: str) -> None:
        logger.info('Salvando texto extraído para documento {}', doc_id)
        save_path = Path('extracted_texts') / f'{doc_id}.txt'
        await save_path.parent.mkdir(parents=True, exist_ok=True)
        await save_path.write_text(extracted_text, encoding='utf-8')
