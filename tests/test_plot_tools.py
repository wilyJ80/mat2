import pytest
from langchain_google_genai._function_utils import convert_to_genai_function_declarations

from mat2.plot_tools import TOOLS, PlotError, build_plot


def test_tool_schemas_convert_for_gemini():
    [tool] = convert_to_genai_function_declarations(TOOLS)
    declarations = {f.name: f for f in tool.function_declarations}
    assert declarations.keys() == {"PlotRevolution", "PlotSurface", "PlotRegion"}
    revolution = declarations["PlotRevolution"].parameters
    assert revolution.properties["axis"].enum == ["x", "y"]
    assert revolution.properties["g"].nullable
    assert set(revolution.required) == {"title", "f", "a", "b"}


def test_revolution_around_x_axis():
    props = build_plot("PlotRevolution", {"title": "t", "f": "sqrt(x)", "a": 0, "b": 4})
    assert props["kind"] == "revolution"
    assert props["f"] == "sqrt(x)"
    assert props["g"] is None
    assert props["axis"] == "x"
    spans = [hi - lo for lo, hi in props["bounds"]]
    assert spans == pytest.approx([spans[0]] * 3)
    x_range, depth, height = props["bounds"]
    assert x_range[0] < 0 and x_range[1] > 4
    assert depth[0] <= -2 and depth[1] >= 2
    assert height[0] <= -2 and height[1] >= 2


def test_revolution_around_shifted_vertical_axis():
    props = build_plot(
        "PlotRevolution", {"title": "t", "f": "x*(2-x)", "a": 0, "b": 2, "axis": "y", "k": -1}
    )
    x_range = props["bounds"][0]
    # raio máximo = |2 - (-1)| = 3
    assert x_range[0] <= -4 and x_range[1] >= 2


def test_washer_keeps_both_functions():
    props = build_plot("PlotRevolution", {"title": "t", "f": "x", "g": "x^2", "a": 0, "b": 1})
    assert props["g"] == "(x ^ 2)"


def test_surface():
    props = build_plot(
        "PlotSurface",
        {"title": "t", "f": "x^2 + y^2", "x_min": -2, "x_max": 2, "y_min": -1, "y_max": 1},
    )
    assert props["bounds"][:2] == [[-2, 2], [-1, 1]]
    z_lo, z_hi = props["bounds"][2]
    assert z_lo <= 0 and z_hi >= 5


def test_region_includes_x_axis():
    props = build_plot("PlotRegion", {"title": "t", "f": "x^2 + 1", "a": 1, "b": 2})
    y_lo, y_hi = props["bounds"][1]
    assert y_lo < 0 and y_hi > 5


@pytest.mark.parametrize(
    ("name", "args", "message"),
    [
        ("PlotRevolution", {"title": "t", "f": "x", "a": 2, "b": 1}, "início deve ser menor"),
        ("PlotRevolution", {"title": "t", "f": "sqrt(x)", "a": -4, "b": -1}, "não está definida"),
        ("PlotRevolution", {"title": "t", "f": "exp(x)", "a": 0, "b": 50}, "grandes demais"),
        ("PlotRevolution", {"title": "t", "f": "foo(x)", "a": 0, "b": 1}, "não suportada"),
        ("PlotRevolution", {"title": "t", "f": "x", "a": 0, "b": 1, "axis": "z"}, "argumentos inválidos"),
        ("PlotRegion", {"title": "t", "f": "x"}, "argumentos inválidos"),
        ("PlotSurface", {"title": "t", "f": "x+z", "x_min": 0, "x_max": 1, "y_min": 0, "y_max": 1}, "'z'"),
        ("Nope", {}, "desconhecida"),
    ],
)
def test_errors_are_reported_to_the_llm(name, args, message):
    with pytest.raises(PlotError, match=message):
        build_plot(name, args)


def test_region_annotations_with_exact_values():
    props = build_plot(
        "PlotRegion",
        {
            "title": "t",
            "f": "sin(x)",
            "g": "cos(x)",
            "a": 0,
            "b": "pi",
            "marks": [{"x": "pi/4"}, {"x": "2", "label": "x = 2"}],
            "points": [{"x": "pi/4", "y": "sqrt(2)/2", "label": "P"}],
        },
    )
    assert props["b"] == pytest.approx(3.14159265)
    assert (props["a_label"], props["b_label"]) == ("0", "π")
    assert props["marks"] == [
        {"x": pytest.approx(0.7853982), "label": "π/4"},
        {"x": 2.0, "label": "x = 2"},
    ]
    assert props["points"] == [{"x": pytest.approx(0.7853982), "y": pytest.approx(0.7071068), "label": "P"}]


def test_annotations_outside_the_interval_expand_the_view():
    props = build_plot("PlotRegion", {"title": "t", "f": "x", "a": 0, "b": 1, "points": [{"x": "3", "y": "5"}]})
    (x_lo, x_hi), (y_lo, y_hi) = props["bounds"]
    assert x_hi > 3 and y_hi > 5


def test_labels_cannot_inject_html():
    props = build_plot(
        "PlotRegion",
        {"title": "t", "f": "x", "a": 0, "b": 1, "marks": [{"x": "0.5", "label": "<img src=x onerror=alert(1)>"}]},
    )
    assert "<" not in props["marks"][0]["label"] and ">" not in props["marks"][0]["label"]


def test_revolution_accepts_expression_bounds():
    props = build_plot("PlotRevolution", {"title": "t", "f": "sin(x)", "a": "0", "b": "pi"})
    assert props["b"] == pytest.approx(3.14159265)


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ({"marks": [{"x": "y"}]}, "nome desconhecido"),
        ({"marks": [{"x": "sqrt(-1)"}]}, "não é um número válido"),
        ({"marks": [{"x": str(i)} for i in range(9)]}, "no máximo"),
    ],
)
def test_invalid_annotations(args, message):
    with pytest.raises(PlotError, match=message):
        build_plot("PlotRegion", {"title": "t", "f": "x", "a": 0, "b": 1, **args})


@pytest.mark.parametrize(
    ("source", "label"),
    [("pi/4", "π/4"), ("2*pi", "2π"), ("3*pi/2", "3π/2"), ("sqrt(2)/2", "√2/2"), ("0.5", "0,5"), ("2", "2")],
)
def test_pretty_labels(source, label):
    from mat2.plot_tools import _pretty

    assert _pretty(source) == label
