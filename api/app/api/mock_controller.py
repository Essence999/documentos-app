from __future__ import annotations

from dataclasses import dataclass

from litestar import Router, delete, get, post, status_codes
from litestar.exceptions import NotFoundException, ValidationException

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


@dataclass
class PanelConfig:
    id: str
    label: str


@dataclass
class PaginatedResponse[T]:
    items: list[T]
    total: int


@dataclass
class Contrato:
    numero_contrato: str
    descricao: str | None = None


@dataclass
class Declaracao:
    numero_declaracao: str
    descricao: str | None = None


@dataclass
class PanelData:
    contratos: list[Contrato]
    declaracoes: list[Declaracao]


@dataclass
class ConfirmPayload:
    numero_contrato: str
    numeros_declaracao: list[str]


# ---------------------------------------------------------------------------
# Mock data store
# ---------------------------------------------------------------------------


_PANELS: list[PanelConfig] = [
    PanelConfig(id=f'panel-{i:02d}', label=f'Painel {i:02d} — Exercício 202{i % 5}') for i in range(1, 26)
]

_PANEL_DATA: dict[str, PanelData] = {
    panel.id: PanelData(
        contratos=[
            Contrato(
                numero_contrato=f'CTR-{panel.id[-2:]}{j:03d}',
                descricao=f'Contrato de prestação de serviços nº {j}',
            )
            for j in range(1, 5)
        ],
        declaracoes=[
            Declaracao(
                numero_declaracao=f'DEC-{panel.id[-2:]}{k:03d}',
                descricao=f'Declaração referente ao período {k}/2024',
            )
            for k in range(1, 7)
        ],
    )
    for panel in _PANELS
}

# Simulates rows deleted via the discard endpoint (resets on restart).
_discarded: set[str] = set()


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


@get('/panels')
def list_panels(page: int = 1, page_size: int = 10) -> PaginatedResponse[PanelConfig]:
    start = (page - 1) * page_size
    end = start + page_size

    return PaginatedResponse(
        items=_PANELS[start:end],
        total=len(_PANELS),
    )


@get('/panels/{panel_id:str}')
def get_panel_data(panel_id: str) -> PanelData:
    if panel_id not in _PANEL_DATA:
        raise NotFoundException(detail=f"Painel '{panel_id}' não encontrado.")

    data = _PANEL_DATA[panel_id]
    return PanelData(
        contratos=data.contratos,
        declaracoes=[d for d in data.declaracoes if d.numero_declaracao not in _discarded],
    )


@post('/confirmar', status_code=status_codes.HTTP_204_NO_CONTENT)
def confirmar(data: ConfirmPayload) -> None:
    all_declaracoes = {d.numero_declaracao for panel_data in _PANEL_DATA.values() for d in panel_data.declaracoes}
    unknown = [n for n in data.numeros_declaracao if n not in all_declaracoes]
    if unknown:
        raise ValidationException(detail=f'Declarações não encontradas: {", ".join(unknown)}')


@delete('/declaracoes/{numero:str}', status_code=status_codes.HTTP_204_NO_CONTENT)
def descartar_declaracao(numero: str) -> None:
    all_declaracoes = {d.numero_declaracao for panel_data in _PANEL_DATA.values() for d in panel_data.declaracoes}
    if numero not in all_declaracoes:
        raise NotFoundException(detail=f"Declaração '{numero}' não encontrada.")
    _discarded.add(numero)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

mock_router = Router(
    path='/api',
    route_handlers=[
        list_panels,
        get_panel_data,
        confirmar,
        descartar_declaracao,
    ],
)
