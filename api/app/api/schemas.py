from datetime import datetime
from enum import StrEnum

import msgspec


class DocumentRecord(msgspec.Struct):
    id: datetime

    @property
    def id_to_str(self) -> str:
        return self.id.isoformat()


class ExtractionResultPayload(msgspec.Struct):
    extracted_text: str | None = None


class ExtractionResultStatus(StrEnum):
    SUCCESS = 'success'
    ERROR = 'error'
