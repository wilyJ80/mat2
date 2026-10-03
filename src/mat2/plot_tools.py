"""Tools de gráficos que a LLM pode chamar.

Cada tool valida os argumentos, amostra as funções para calcular os limites do
gráfico e devolve as props do elemento `Plot` (public/elements/Plot.jsx).
"""

import re
from typing import Annotated, Literal

import chainlit as cl
from pydantic import BaseModel, BeforeValidator, Field, ValidationError

from mat2.expressions import Expression, ExpressionError

SAMPLES = 200
MAX_ABS_VALUE = 1e4
EXPRESSION_HELP = (
    "Sintaxe: x^2, sqrt(x), sin(x), exp(x), log(x) (logaritmo natural), abs(x), pi, e. "
    "Multiplicação sempre explícita: 2*x."
)


MAX_ANNOTATIONS = 8
MAX_LABEL_LENGTH = 24


class PlotError(ValueError):
    pass


# Número escrito como expressão constante ("0", "pi/4", "sqrt(2)/2"). O valor
# exato vira rótulo legível no gráfico ("π/4") em vez de "0,785". Números que
# chegarem como int/float também são aceitos.
NumberExpr = Annotated[str, BeforeValidator(lambda v: str(v) if isinstance(v, (int, float)) else v)]


class Mark(BaseModel):
    x: NumberExpr = Field(description="Posição em x, como número ou expressão constante, ex.: pi/4")
    label: str | None = Field(default=None, description="Rótulo curto; padrão: o próprio valor de x")


class Point(BaseModel):
    x: NumberExpr = Field(description="Coordenada x, ex.: pi/4")
    y: NumberExpr = Field(description="Coordenada y, ex.: sqrt(2)/2")
    label: str | None = Field(default=None, description="Rótulo curto, ex.: P ou (π/4, √2/2)")


class PlotRevolution(BaseModel):
    """Mostra em 3D o sólido de revolução gerado ao girar a região sob y = f(x)
    (ou entre y = f(x) e y = g(x), método das arruelas/cascas) em torno de um eixo.
    Use para volume de sólidos de revolução e área de superfície de revolução."""

    title: str = Field(description="Título curto do gráfico, ex.: 'y = √x girando em torno do eixo x'")
    f: str = Field(description=f"Função de x que gera o sólido. {EXPRESSION_HELP}")
    g: str | None = Field(
        default=None,
        description="Segunda função de x, opcional, para sólidos com furo (arruelas). Omita se não houver.",
    )
    a: NumberExpr = Field(description="Início do intervalo em x (número ou expressão, ex.: 0, pi/2)")
    b: NumberExpr = Field(description="Fim do intervalo em x (número ou expressão, ex.: 4, pi)")
    axis: Literal["x", "y"] = Field(
        default="x",
        description="'x' = gira em torno de uma reta horizontal y = k; 'y' = gira em torno de uma reta vertical x = k",
    )
    k: float = Field(default=0, description="Posição do eixo de rotação (0 = o próprio eixo x ou y)")


class PlotSurface(BaseModel):
    """Mostra em 3D a superfície z = f(x, y) num domínio retangular."""

    title: str = Field(description="Título curto do gráfico")
    f: str = Field(description=f"Função de x e y. {EXPRESSION_HELP}")
    x_min: float
    x_max: float
    y_min: float
    y_max: float


class PlotRegion(BaseModel):
    """Mostra em 2D a região entre y = f(x) e y = g(x) (ou entre f e o eixo x)
    no intervalo [a, b], com o intervalo destacado no eixo x. Use para área entre
    curvas e para ilustrar comprimento de arco. Use `marks` e `points` para
    apontar o que importa na resolução: onde as curvas se cruzam, pontos de
    interseção, onde a curva de cima muda."""

    title: str = Field(description="Título curto do gráfico")
    f: str = Field(description=f"Função de x. {EXPRESSION_HELP}")
    g: str | None = Field(default=None, description="Segunda função de x, opcional (padrão: eixo x, y = 0)")
    a: NumberExpr = Field(description="Início do intervalo em x (número ou expressão, ex.: 0, pi/4)")
    b: NumberExpr = Field(description="Fim do intervalo em x (número ou expressão, ex.: 2, pi)")
    marks: list[Mark] = Field(
        default_factory=list,
        description="Linhas verticais tracejadas com rótulo em valores de x importantes dentro do "
        "intervalo, ex.: onde as curvas se cruzam e a integral precisa ser dividida",
    )
    points: list[Point] = Field(
        default_factory=list,
        description="Pontos destacados com rótulo, ex.: interseções das curvas",
    )


TOOLS = [PlotRevolution, PlotSurface, PlotRegion]


def _expr(source: str, variables: tuple[str, ...] = ("x",)) -> Expression:
    try:
        return Expression(source, variables)
    except ExpressionError as exc:
        raise PlotError(f"{exc}. {EXPRESSION_HELP}") from exc


def _number(source: str, what: str) -> float:
    value = _expr(source, ())()
    if value is None:
        raise PlotError(f"{what} '{source}' não é um número válido")
    if abs(value) > MAX_ABS_VALUE:
        raise PlotError(f"{what} '{source}' grande demais")
    return value


def _label(text: str) -> str:
    """Texto curto e seguro para exibir no gráfico (o JSXGraph renderiza HTML)."""
    return re.sub(r"[<>&\"'`]", "", text).strip()[:MAX_LABEL_LENGTH]


def _pretty(source: str) -> str:
    """Rótulo legível a partir de uma expressão constante: 'pi/4' -> 'π/4'."""
    text = source.strip().replace("**", "^").replace(" ", "")
    try:
        return f"{float(text):g}".replace(".", ",")
    except ValueError:
        pass
    text = re.sub(r"\bpi\b", "π", text)
    text = re.sub(r"sqrt\(([^()]+)\)", lambda m: "√" + (m[1] if len(m[1]) == 1 else f"({m[1]})"), text)
    text = re.sub(r"(?<=[\d)])\*(?=[π√(a-z])", "", text)
    return _label(text.replace("*", "·"))


def _check_interval(lo: float, hi: float, name: str = "intervalo") -> None:
    if not lo < hi:
        raise PlotError(f"{name} inválido: o início deve ser menor que o fim")
    if max(abs(lo), abs(hi)) > MAX_ABS_VALUE:
        raise PlotError(f"{name} grande demais")


def _linspace(lo: float, hi: float, n: int = SAMPLES) -> list[float]:
    return [lo + (hi - lo) * i / (n - 1) for i in range(n)]


def _values(expr: Expression, *grids: list[float]) -> list[float]:
    if len(grids) == 1:
        points = [(x,) for x in grids[0]]
    else:
        points = [(x, y) for x in grids[0] for y in grids[1]]
    values = [v for p in points if (v := expr(*p)) is not None]
    if not values:
        raise PlotError(f"'{expr.source}' não está definida em nenhum ponto do intervalo")
    if max(abs(v) for v in values) > MAX_ABS_VALUE:
        raise PlotError(f"'{expr.source}' assume valores grandes demais no intervalo; reduza o intervalo")
    return values


def _pad(lo: float, hi: float, ratio: float = 0.08) -> list[float]:
    span = hi - lo or 1.0
    return [lo - span * ratio, hi + span * ratio]


def _revolution(args: PlotRevolution) -> dict:
    a, b = _number(args.a, "início do intervalo"), _number(args.b, "fim do intervalo")
    _check_interval(a, b)
    xs = _linspace(a, b)
    funcs = [_expr(args.f)] + ([_expr(args.g)] if args.g else [])
    ys = [v for f in funcs for v in _values(f, xs)]

    # O plano da curva (x, y) vira o plano vertical (x, 0, z) da cena 3D,
    # com a profundidade (eixo y da cena) surgindo da rotação.
    if args.axis == "x":
        radius = max(abs(y - args.k) for y in ys)
        bounds = [_pad(a, b), _pad(-radius, radius), _pad(args.k - radius, args.k + radius)]
    else:
        radius = max(abs(a - args.k), abs(b - args.k))
        bounds = [_pad(args.k - radius, args.k + radius), _pad(-radius, radius), _pad(min(ys), max(ys))]

    # Mesma escala nos três eixos, para o sólido não aparecer distorcido.
    span = max(hi - lo for lo, hi in bounds)
    bounds = [[(lo + hi - span) / 2, (lo + hi + span) / 2] for lo, hi in bounds]

    return {
        "kind": "revolution",
        "title": args.title,
        "f": funcs[0].jessie,
        "g": funcs[1].jessie if args.g else None,
        "a": a,
        "b": b,
        "axis": args.axis,
        "k": args.k,
        "bounds": bounds,
    }


def _surface(args: PlotSurface) -> dict:
    _check_interval(args.x_min, args.x_max, "intervalo de x")
    _check_interval(args.y_min, args.y_max, "intervalo de y")
    f = _expr(args.f, ("x", "y"))
    zs = _values(f, _linspace(args.x_min, args.x_max, 40), _linspace(args.y_min, args.y_max, 40))
    return {
        "kind": "surface",
        "title": args.title,
        "f": f.jessie,
        "bounds": [[args.x_min, args.x_max], [args.y_min, args.y_max], _pad(min(zs), max(zs))],
    }


def _region(args: PlotRegion) -> dict:
    a, b = _number(args.a, "início do intervalo"), _number(args.b, "fim do intervalo")
    _check_interval(a, b)
    if len(args.marks) + len(args.points) > MAX_ANNOTATIONS:
        raise PlotError(f"no máximo {MAX_ANNOTATIONS} marcações e pontos no total")
    xs = _linspace(a, b)
    f = _expr(args.f)
    g = _expr(args.g) if args.g else None
    ys = _values(f, xs) + (_values(g, xs) if g else [0.0])

    marks = [
        {"x": _number(m.x, "marcação"), "label": _label(m.label) if m.label else _pretty(m.x)}
        for m in args.marks
    ]
    points = [
        {"x": _number(p.x, "ponto"), "y": _number(p.y, "ponto"), "label": _label(p.label) if p.label else ""}
        for p in args.points
    ]
    all_x = [a, b] + [m["x"] for m in marks] + [p["x"] for p in points]
    all_y = ys + [0.0] + [p["y"] for p in points]

    return {
        "kind": "region",
        "title": args.title,
        "f": f.jessie,
        "g": g.jessie if g else None,
        "a": a,
        "b": b,
        "a_label": _pretty(args.a),
        "b_label": _pretty(args.b),
        "marks": marks,
        "points": points,
        "bounds": [_pad(min(all_x), max(all_x), 0.15), _pad(min(all_y), max(all_y), 0.15)],
    }


BUILDERS = {
    PlotRevolution.__name__: (PlotRevolution, _revolution),
    PlotSurface.__name__: (PlotSurface, _surface),
    PlotRegion.__name__: (PlotRegion, _region),
}


def build_plot(name: str, raw_args: dict) -> dict:
    """Valida os argumentos de uma chamada de tool e devolve as props do gráfico."""
    if name not in BUILDERS:
        raise PlotError(f"tool desconhecida: {name}")
    model, builder = BUILDERS[name]
    try:
        args = model.model_validate(raw_args)
    except ValidationError as exc:
        raise PlotError(f"argumentos inválidos: {exc.errors(include_url=False)}") from exc
    return builder(args)


def plot_element(props: dict) -> cl.CustomElement:
    return cl.CustomElement(name="Plot", props=props, display="inline")
