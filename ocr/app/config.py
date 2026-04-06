from dataclasses import dataclass
import os
from pathlib import Path
import sys

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

os.environ['OMP_THREAD_LIMIT'] = '1'


logger.remove()
logger.add(sys.stdout, enqueue=True, level='INFO', backtrace=False, diagnose=False)

logger.add(
    'logs/app.log',
    rotation='10 MB',
    retention='1 month',
    level='DEBUG',
    serialize=True,
    enqueue=True,
    backtrace=False,
    diagnose=False,
)


@dataclass(frozen=True)
class Config:
    """Configurações globais da aplicação, carregadas do ambiente e definidas
    como constantes imutáveis para garantir consistência e segurança.
    """

    docs_dir: Path
    api_base_url: str
    internal_service_key: str
    tessdata_path: Path
    lang: str
    dpi: int
    min_pdf_size_bytes: int
    supported_extensions: frozenset[str]
    image_extensions: frozenset[str]


SUPPORTED_EXTENSIONS = frozenset({'.pdf', '.jpg', '.jpeg', '.png', '.gif'})
IMAGE_EXTENSIONS = SUPPORTED_EXTENSIONS - {'.pdf'}
DPI = 300
MIN_PDF_SIZE_BYTES = 15 * 1024  # 15 KB, heurística para arquivos PDF válidos

settings = Config(
    docs_dir=Path(os.environ.get('DOCS_PATH', 'documents')),
    api_base_url=os.environ.get('API_BASE_URL', 'http://localhost:8000/documents'),
    internal_service_key=os.environ['INTERNAL_SERVICE_KEY'],
    tessdata_path=Path('/usr/share/tesseract-ocr/5/tessdata'),
    lang='por',
    dpi=300,
    min_pdf_size_bytes=MIN_PDF_SIZE_BYTES,
    supported_extensions=SUPPORTED_EXTENSIONS,
    image_extensions=IMAGE_EXTENSIONS,
)
