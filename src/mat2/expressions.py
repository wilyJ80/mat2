"""Validação segura das expressões matemáticas enviadas pela LLM.

As expressões são analisadas com `ast` (nunca com `eval`) contra uma whitelist
de nós, variáveis e funções. Depois são reescritas na sintaxe do JessieCode,
que é o que o JSXGraph interpreta no frontend. Essa whitelist é a barreira de
segurança: o JessieCode sozinho não impede chamadas arbitrárias.
"""

import ast
import math
import re

FUNCTIONS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "sqrt": math.sqrt,
    "exp": math.exp,
    "log": math.log,
    "abs": abs,
}

# Nomes alternativos que a LLM costuma usar.
FUNCTION_ALIASES = {"ln": "log", "sen": "sin", "tg": "tan", "arcsin": "asin", "arccos": "acos", "arctan": "atan"}

CONSTANTS = {"pi": math.pi, "e": math.e}

# Como cada constante é escrita no JessieCode.
JESSIE_CONSTANTS = {"pi": "PI", "e": "EULER"}

MAX_LENGTH = 200

BINARY_OPS = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.Pow: "^"}


class ExpressionError(ValueError):
    pass


def _normalize(expr: str) -> str:
    expr = expr.strip().replace("^", "**").replace("π", "pi")
    # "y = x^2" -> "x^2"
    expr = re.sub(r"^\s*[a-z]\s*(\(\s*[a-z,\s]*\))?\s*=", "", expr, flags=re.IGNORECASE)
    for alias, name in FUNCTION_ALIASES.items():
        expr = re.sub(rf"\b{alias}\s*\(", f"{name}(", expr)
    return expr.strip()


def _check(node: ast.AST, variables: tuple[str, ...]) -> None:
    match node:
        case ast.Expression(body=body):
            _check(body, variables)
        case ast.Constant(value=value) if isinstance(value, (int, float)) and not isinstance(value, bool):
            pass
        case ast.Name(id=name) if name in variables or name in CONSTANTS:
            pass
        case ast.Name(id=name):
            raise ExpressionError(f"nome desconhecido '{name}' (variáveis permitidas: {', '.join(variables)})")
        case ast.BinOp(left=left, op=op, right=right) if type(op) in BINARY_OPS:
            _check(left, variables)
            _check(right, variables)
        case ast.UnaryOp(op=ast.USub() | ast.UAdd(), operand=operand):
            _check(operand, variables)
        case ast.Call(func=ast.Name(id=name), args=args, keywords=[]) if name in FUNCTIONS and len(args) == 1:
            _check(args[0], variables)
        case ast.Call(func=ast.Name(id=name)):
            raise ExpressionError(f"função não suportada '{name}' (use: {', '.join(FUNCTIONS)})")
        case _:
            raise ExpressionError(f"construção não suportada: {ast.dump(node)[:60]}")


def _to_jessie(node: ast.AST) -> str:
    match node:
        case ast.Expression(body=body):
            return _to_jessie(body)
        case ast.Constant(value=value):
            return repr(value)
        case ast.Name(id=name):
            return JESSIE_CONSTANTS.get(name, name)
        case ast.BinOp(left=left, op=op, right=right):
            return f"({_to_jessie(left)} {BINARY_OPS[type(op)]} {_to_jessie(right)})"
        case ast.UnaryOp(op=ast.USub(), operand=operand):
            return f"(-{_to_jessie(operand)})"
        case ast.UnaryOp(operand=operand):
            return _to_jessie(operand)
        case ast.Call(func=ast.Name(id=name), args=[arg]):
            return f"{name}({_to_jessie(arg)})"
    raise ExpressionError("expressão inválida")


class Expression:
    """Expressão validada, avaliável em Python e exportável para JessieCode."""

    def __init__(self, source: str, variables: tuple[str, ...]):
        if len(source) > MAX_LENGTH:
            raise ExpressionError(f"expressão muito longa (máx. {MAX_LENGTH} caracteres)")
        normalized = _normalize(source)
        try:
            tree = ast.parse(normalized, mode="eval")
        except SyntaxError as exc:
            raise ExpressionError(f"sintaxe inválida em '{source}'") from exc
        _check(tree, variables)
        self.source = source
        self.variables = variables
        self.jessie = _to_jessie(tree)
        # Constantes inteiras viram float para que algo como 9**9**9 estoure
        # com OverflowError em vez de travar calculando um inteiro gigante.
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant):
                node.value = float(node.value)
        self._code = compile(tree, "<expr>", "eval")

    def __call__(self, *values: float) -> float | None:
        scope = {**FUNCTIONS, **CONSTANTS, **dict(zip(self.variables, values))}
        try:
            result = eval(self._code, {"__builtins__": {}}, scope)  # árvore já validada pela whitelist
        except (ValueError, ZeroDivisionError, OverflowError):
            return None
        if isinstance(result, complex) or not math.isfinite(result):
            return None
        return float(result)
