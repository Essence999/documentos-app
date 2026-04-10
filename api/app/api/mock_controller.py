from __future__ import annotations

from dataclasses import dataclass
from litestar import status_codes
from litestar import Router, delete, get, post
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
    numeros_processo: list[str]
    descricao: str | None = None


@dataclass
class Declaracao:
    numero_declaracao: str
    numero_processo: str
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

_PROCESSOS = [f'PRC-{i:03d}' for i in range(1, 100)]


def _build_panel_data(panel_id: str) -> PanelData:
    """
    Generates deterministic mock data for a panel.

    Distribution (chosen so colour bars are visually interesting):
      CTR-xx001: PROC-001 + PROC-002  (bicolor)
      CTR-xx002: PROC-003             (solid, shared with CTR-003)
      CTR-xx003: PROC-003 + PROC-004  (bicolor)
      CTR-xx004: (no processo)        (no bar)

      DEC-xx001/002: PROC-001
      DEC-xx003/004: PROC-003
      DEC-xx005:     PROC-004
      DEC-xx006:     PROC-002
    """
    s = panel_id[-2:]
    P = _PROCESSOS  # NOQA

    contratos = [
        Contrato(f'CTR-{s}001', [P[0], P[1], P[5]], 'Contrato de prestação de serviços nº 1'),
        Contrato(f'CTR-{s}002', [P[2], P[1]], 'Contrato de prestação de serviços nº 2'),
        Contrato(f'CTR-{s}004', [], 'Contrato de prestação de serviços nº 4'),
        Contrato(f'CTR-{s}003', [P[2], P[3]], 'Contrato de prestação de serviços nº 3'),
    ]

    declaracoes = [
        Declaracao(f'DEC-{s}001', P[0], 'Declaração referente ao período 1/2024'),
        Declaracao(f'DEC-{s}002', P[0], 'Declaração referente ao período 2/2024'),
        Declaracao(f'DEC-{s}003', P[2], 'Declaração referente ao período 3/2024'),
        Declaracao(f'DEC-{s}004', P[2], 'Declaração referente ao período 4/2024'),
        Declaracao(f'DEC-{s}005', P[3], 'Declaração referente ao período 5/2024'),
        Declaracao(f'DEC-{s}006', P[1], 'Declaração referente ao período 6/2024'),
    ]

    return PanelData(contratos=contratos, declaracoes=declaracoes)


_PANEL_DATA: dict[str, PanelData] = {p.id: _build_panel_data(p.id) for p in _PANELS}

_discarded: set[str] = set()


# ---------------------------------------------------------------------------
# Ordering helpers
# ---------------------------------------------------------------------------


def _contrato_sort_key(c: Contrato) -> str:
    # Primary process (lexicographic min). Contracts with no process sort last.
    return min(c.numeros_processo) if c.numeros_processo else '\xff'


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


@get('/panels')
def list_panels(page: int = 1, page_size: int = 10) -> PaginatedResponse[PanelConfig]:
    start = (page - 1) * page_size
    return PaginatedResponse(items=_PANELS[start : start + page_size], total=len(_PANELS))


@get('/panels/{panel_id:str}')
def get_panel_data(panel_id: str) -> PanelData:
    if panel_id not in _PANEL_DATA:
        raise NotFoundException(detail=f"Painel '{panel_id}' não encontrado.")

    data = _PANEL_DATA[panel_id]

    contratos = sorted(data.contratos, key=_contrato_sort_key)
    declaracoes = sorted(
        (d for d in data.declaracoes if d.numero_declaracao not in _discarded),
        key=lambda d: d.numero_processo,
    )

    return PanelData(contratos=contratos, declaracoes=declaracoes)


@post('/confirmar', status_code=status_codes.HTTP_204_NO_CONTENT)
def confirmar(data: ConfirmPayload) -> None:
    all_declaracoes = {d.numero_declaracao for pd in _PANEL_DATA.values() for d in pd.declaracoes}
    unknown = [n for n in data.numeros_declaracao if n not in all_declaracoes]
    if unknown:
        raise ValidationException(detail=f'Declarações não encontradas: {", ".join(unknown)}')


@delete('/declaracoes/{numero:str}', status_code=status_codes.HTTP_204_NO_CONTENT)
def descartar_declaracao(numero: str) -> None:
    all_declaracoes = {d.numero_declaracao for pd in _PANEL_DATA.values() for d in pd.declaracoes}
    if numero not in all_declaracoes:
        raise NotFoundException(detail=f"Declaração '{numero}' não encontrada.")
    _discarded.add(numero)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

mock_router = Router(
    path='/api',
    route_handlers=[list_panels, get_panel_data, confirmar, descartar_declaracao],
)
