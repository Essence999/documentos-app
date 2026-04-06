from pathlib import Path
import time
from typing import cast

import httpx
import numpy as np
from PIL import Image
import pymupdf

from app.config import logger, settings
from app.ocr_engine import run_ocr


def transmit(doc_id: str, text: str | None, http_client: httpx.Client, retries: int = 5) -> None:
    """Envia o resultado da extração para o endpoint da API.

    Texto presente indica sucesso, None indica falha na
    extração. Isso garante que a API sempre possa deletar o arquivo e atualizar
    o estado, independentemente do resultado.

    Args:
        doc_id:      Identificador do documento (stem do nome do arquivo).
        text:        Texto extraído, ou None em caso de falha/ausência de conteúdo.
        http_client: Cliente HTTP compartilhado entre threads.
        retries:     Número máximo de tentativas com backoff exponencial.

    Raises:
        httpx.HTTPError: Se todas as tentativas falharem.
    """
    url = f'{settings.api_base_url}/{doc_id}/extraction-result'

    for attempt in range(1, retries + 1):
        try:
            response = http_client.patch(url, json={'extracted_text': text})
            response.raise_for_status()
            return
        except httpx.HTTPError:
            if attempt == retries:
                raise
            wait = 2**attempt
            logger.warning(
                '[{doc_id}] Tentativa {attempt}/{retries} falhou — aguardando {wait}s',
                doc_id=doc_id,
                attempt=attempt,
                retries=retries,
                wait=wait,
            )
            time.sleep(wait)


def _extract_from_pdf(pdf_path: Path, doc_id: str) -> str:
    """Extrai texto de todas as páginas de um PDF.

    Usa texto nativo quando disponível na página; recorre a OCR quando a página
    é composta apenas por imagens (scan). O PyMuPDF renderiza cada página em um
    Pixmap (buffer de bytes brutos), que é convertido para array NumPy e depois
    para PIL Image antes de ser enviado ao Tesseract.

    Args:
        pdf_path: Caminho para o arquivo PDF.
        doc_id:   Identificador usado no logging.

    Returns:
        Texto completo extraído, blocos separados por linha em branco. Pode ser vazio.

    Raises:
        ValueError:            Se o arquivo for muito pequeno ou não tiver assinatura PDF.
        pymupdf.FileDataError: Se o arquivo estiver corrompido ou não for um PDF válido.
    """
    with pdf_path.open('rb') as f:
        if not f.read(5).startswith(b'%PDF-'):
            raise ValueError('Magic number ausente — possível JSON/HTML no lugar do PDF')

    if pdf_path.stat().st_size < settings.min_pdf_size_bytes:
        raise ValueError(f'Arquivo vazio ou truncado ({pdf_path.stat().st_size} bytes)')

    extracted_text_blocks: list[str] = []

    with pymupdf.open(pdf_path) as doc:
        total_pages = len(doc)
        for page_index in range(total_pages):
            page_num = page_index + 1
            page = doc[page_index]
            native_text = cast('str', page.get_text('text')).strip()

            if native_text:
                extracted_text_blocks.append(native_text)
                logger.debug(
                    '[{doc_id}] Página {}/{} → texto nativo)',
                    page_num,
                    total_pages,
                    doc_id=doc_id,
                )
            else:
                pix = page.get_pixmap(dpi=settings.dpi, colorspace=pymupdf.csRGB, alpha=False)
                samples = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                ocr_text = run_ocr(Image.fromarray(samples))
                if ocr_text:
                    extracted_text_blocks.append(ocr_text)
                logger.debug(
                    '[{doc_id}] Página {}/{} → OCR)',
                    page_num,
                    total_pages,
                    doc_id=doc_id,
                )
    return '\n\n'.join(extracted_text_blocks).strip()


def _extract_from_image(image_path: Path) -> str:
    """Extrai texto de um arquivo de imagem via OCR.

    O PIL decodifica o formato nativamente (JPEG, PNG, GIF), entregando um
    objeto Image pronto — sem conversão manual de buffer, ao contrário do PDF.
    Para GIFs, processa apenas o primeiro frame.

    Args:
        image_path: Caminho para o arquivo de imagem.

    Returns:
        Texto extraído. Pode ser vazio.

    Raises:
        PIL.UnidentifiedImageError: Se o arquivo estiver corrompido ou não for
            uma imagem reconhecida.
    """
    return run_ocr(Image.open(image_path))


def process_doc(file_path: Path, http_client: httpx.Client) -> str:
    """Extrai texto de um documento (PDF ou imagem) e transmite para a API.

    Sempre notifica a API ao final — com o texto em caso de sucesso, ou None
    em caso de falha na extração. Isso garante que a API possa deletar o arquivo
    e atualizar o estado independentemente do resultado, evitando arquivos órfãos.

    Apenas falhas de transmissão são re-lançadas, pois nesse caso o arquivo
    deve permanecer na pasta para ser reprocessado no próximo startup.

    Args:
        file_path:   Caminho para o arquivo a ser processado.
        http_client: Cliente HTTP compartilhado entre threads.

    Returns:
        Identificador do documento processado (stem do nome do arquivo).

    Raises:
        httpx.HTTPError: Se a transmissão falhar após todas as tentativas.
    """
    doc_id = file_path.stem
    is_pdf = file_path.suffix.lower() == '.pdf'
    file_type = 'PDF' if is_pdf else 'Imagem'

    logger.info('[{doc_id}] Iniciando extração de {file_type}', doc_id=doc_id, file_type=file_type)

    text: str | None = None
    try:
        result = _extract_from_pdf(file_path, doc_id) if is_pdf else _extract_from_image(file_path)
        text = result or None
        if text is None:
            logger.warning('[{doc_id}] Nenhum texto extraído', doc_id=doc_id)
    except Exception as e:  # noqa: BLE001
        logger.error('[{doc_id}] Falha na extração: {e}', doc_id=doc_id, e=e)

    try:
        transmit(doc_id, text, http_client)
        text_bytes = len(text) if text else 0
        logger.success(
            '[{doc_id}] Processado e API notificada ({text_bytes:,} bytes)', doc_id=doc_id, text_bytes=text_bytes
        )
    except Exception:
        logger.exception('[{doc_id}] Falha na transmissão — arquivo mantido para reprocessamento', doc_id=doc_id)
        raise

    return doc_id
