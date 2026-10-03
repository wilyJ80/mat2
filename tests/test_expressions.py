import math

import pytest

from mat2.expressions import Expression, ExpressionError


@pytest.mark.parametrize(
    ("source", "x", "expected"),
    [
        ("x^2", 3, 9),
        ("x**2", 3, 9),
        ("sqrt(x)", 4, 2),
        ("2*x^3 - sqrt(x) + sin(pi*x)", 1, 1),
        ("ln(x)", math.e, 1),
        ("sen(x)", 0, 0),
        ("e^x", 0, 1),
        ("y = x + 1", 1, 2),
        ("f(x) = abs(x)", -2, 2),
        ("-x", 2, -2),
    ],
)
def test_evaluates(source, x, expected):
    assert Expression(source, ("x",))(x) == pytest.approx(expected)


def test_two_variables():
    assert Expression("x^2 + y^2", ("x", "y"))(1, 2) == pytest.approx(5)


@pytest.mark.parametrize("x", [-1, 0])
def test_undefined_points_return_none(x):
    assert Expression("sqrt(x) / x", ("x",))(x) is None


def test_overflow_returns_none_instead_of_hanging():
    assert Expression("9^9^9", ("x",))(1) is None


@pytest.mark.parametrize(
    "source",
    [
        "__import__('os').system('echo')",
        "x.__class__",
        "open('f')",
        "[x for x in ()]",
        "lambda: 1",
        "y + 1",
        "sin(x, 2)",
        "x if x else 1",
        "'abc'",
        "x" * 300,
        "2x",
    ],
)
def test_rejects(source):
    with pytest.raises(ExpressionError):
        Expression(source, ("x",))


@pytest.mark.parametrize(
    ("source", "jessie"),
    [
        ("x**2", "(x ^ 2)"),
        ("pi*e", "(PI * EULER)"),
        ("-sqrt(x)", "(-sqrt(x))"),
        ("ln(x)", "log(x)"),
    ],
)
def test_jessie_output(source, jessie):
    assert Expression(source, ("x",)).jessie == jessie
