from datetime import datetime, timedelta

from app.api.schemas import DocumentRecord

unique_date = datetime.strptime('2024-01-01T00:00:00', '%Y-%m-%dT%H:%M:%S')
documents = [DocumentRecord(id=unique_date + timedelta(minutes=i)) for i in range(100)]


class DocumentRepositoryMock:
    def __init__(self) -> None:
        self.documents = documents

    def count_documents(self) -> int:
        return len(self.documents)

    def get_documents(self) -> list[DocumentRecord]:
        return self.documents

    @staticmethod
    def get_document_pdf_by_id(doc_id: str) -> bytes:
        return f'%PDF-PDF content for document {doc_id}'.encode()
