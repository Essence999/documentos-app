import threading
from typing import cast

import cv2
import numpy as np
from PIL import Image
from tesserocr import OEM, PSM, PyTessBaseAPI

from app.config import settings

_thread_local = threading.local()


def get_tesseract_api() -> PyTessBaseAPI:
    """Retorna a instância do Tesseract associada à thread atual.

    Cria a instância na primeira chamada de cada thread e a reutiliza nas
    subsequentes, garantindo isolamento sem overhead de inicialização repetida.
    """
    if not hasattr(_thread_local, 'api'):
        api = PyTessBaseAPI(
            path=settings.tessdata_path.as_posix(),
            lang=settings.lang,
            oem=cast(OEM, OEM.LSTM_ONLY),  # noqa: TC006
            psm=cast(PSM, PSM.AUTO),  # noqa: TC006
        )
        api.SetVariable('invert_threshold', '0.0')
        _thread_local.api = api
    return _thread_local.api


def preprocess_for_ocr(image: Image.Image) -> Image.Image:
    """Binariza uma imagem via threshold de Otsu para maximizar acurácia do OCR.

    Args:
        image: Imagem PIL em qualquer modo de cor.

    Returns:
        Imagem PIL binarizada (modo 'L', valores 0 ou 255).
    """
    img_array = np.array(image.convert('RGB'))
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    return Image.fromarray(thresh)


def run_ocr(image: Image.Image) -> str:
    """Executa OCR sobre uma imagem PIL e retorna o texto extraído.

    Garante que o estado interno do Tesseract seja limpo após cada execução,
    mesmo em caso de exceção, evitando contaminação entre páginas consecutivas.

    Args:
        image: Imagem PIL a ser reconhecida.

    Returns:
        Texto extraído, sem espaços nas extremidades. Pode ser vazio.
    """
    tess_api = get_tesseract_api()
    preprocessed = preprocess_for_ocr(image)
    tess_api.SetImage(preprocessed)
    try:
        return tess_api.GetUTF8Text().strip()
    finally:
        tess_api.Clear()
