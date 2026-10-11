import ast
import math
import operator
import re


_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def normalize_expression(expression: str) -> str:
    """Normalize arithmetic text without losing parentheses or operators."""

    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("Please provide a non-empty arithmetic expression.")

    normalized = expression.strip().lower()

    replacements = [
        (r"\bdivided\s+by\s+zero\b", "/ 0"),
        (r"\bdivided\s+by\s+([-+]?\d+(?:\.\d+)?)\b", r"/ \1"),
        (r"\bmultiplied\s+by\b", "*"),
        (r"\btimes\b", "*"),
        (r"\bplus\b", "+"),
        (r"\bminus\b", "-"),
        (r"\bmodulo\b", "%"),
        (r"\bmod\b", "%"),
    ]

    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized)

    normalized = normalized.strip()

    # First preserve the entire input if it is already valid Python
    # arithmetic syntax. Parentheses and operator precedence remain intact.
    try:
        ast.parse(normalized, mode="eval")
        return normalized
    except SyntaxError:
        pass

    # Otherwise, extract arithmetic from surrounding natural language.
    number = r"(?:\d+(?:\.\d+)?)"
    atom = rf"(?:{number}|\([^()]*\))"
    arithmetic_operator = r"(?:\*\*|//|[+\-*/%])"

    pattern = re.compile(
        rf"(?<![\w.]){atom}"
        rf"(?:\s*{arithmetic_operator}\s*{atom})+"
    )

    candidates = pattern.findall(normalized)

    if not candidates:
        raise ValueError("Could not identify a supported arithmetic expression.")

    return max(candidates, key=len).replace(" ", "")


def calculate(expression: str) -> dict:
    """Safely evaluate arithmetic without executing arbitrary Python code."""

    normalized = expression

    try:
        normalized = normalize_expression(expression)
        tree = ast.parse(normalized, mode="eval")

        def evaluate(node):
            if isinstance(node, ast.Expression):
                return evaluate(node.body)

            if isinstance(node, ast.Constant):
                if isinstance(node.value, bool) or not isinstance(
                    node.value, (int, float)
                ):
                    raise ValueError("Only numeric values are allowed.")

                if abs(node.value) > 1e12:
                    raise ValueError("Numeric value is too large.")

                return node.value

            if isinstance(node, ast.BinOp):
                operation = _ALLOWED_OPERATORS.get(type(node.op))
                if operation is None:
                    raise ValueError("Operator is not allowed.")

                left = evaluate(node.left)
                right = evaluate(node.right)

                if isinstance(node.op, ast.Pow) and abs(right) > 10:
                    raise ValueError("Exponent is too large.")

                if (
                    isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod))
                    and right == 0
                ):
                    raise ZeroDivisionError(
                        "Division by zero is undefined. No numerical result exists."
                    )

                result = operation(left, right)

                if isinstance(result, bool) or not isinstance(
                    result, (int, float)
                ):
                    raise ValueError("Result must be numeric.")

                if not math.isfinite(result) or abs(result) > 1e15:
                    raise ValueError("Result is outside the permitted range.")

                return result

            if isinstance(node, ast.UnaryOp):
                operation = _ALLOWED_OPERATORS.get(type(node.op))
                if operation is None:
                    raise ValueError("Unary operator is not allowed.")

                result = operation(evaluate(node.operand))

                if not math.isfinite(result) or abs(result) > 1e15:
                    raise ValueError("Result is outside the permitted range.")

                return result

            raise ValueError("Expression contains unsupported syntax.")

        value = evaluate(tree)

        return {
            "success": True,
            "expression": normalized,
            "result": value,
            "error": None,
        }

    except (
        ValueError,
        TypeError,
        SyntaxError,
        ZeroDivisionError,
        OverflowError,
    ) as exc:
        return {
            "success": False,
            "expression": normalized,
            "result": None,
            "error": str(exc),
        }
