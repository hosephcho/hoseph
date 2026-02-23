"""
수학 계산 플러그인

Semantic Kernel의 @kernel_function 데코레이터를 사용하여
AI가 호출할 수 있는 네이티브 함수(Tool)를 정의합니다.

이 플러그인은 Auto Function Calling Agent 예제에서 사용됩니다.
"""

import math
from semantic_kernel.functions import kernel_function


class MathPlugin:
    """기본 수학 연산을 제공하는 플러그인"""

    @kernel_function(
        name="add",
        description="두 숫자를 더합니다",
    )
    def add(self, number1: float, number2: float) -> str:
        """두 숫자의 합을 반환합니다"""
        result = number1 + number2
        return f"{number1} + {number2} = {result}"

    @kernel_function(
        name="subtract",
        description="첫 번째 숫자에서 두 번째 숫자를 뺍니다",
    )
    def subtract(self, number1: float, number2: float) -> str:
        """두 숫자의 차를 반환합니다"""
        result = number1 - number2
        return f"{number1} - {number2} = {result}"

    @kernel_function(
        name="multiply",
        description="두 숫자를 곱합니다",
    )
    def multiply(self, number1: float, number2: float) -> str:
        """두 숫자의 곱을 반환합니다"""
        result = number1 * number2
        return f"{number1} × {number2} = {result}"

    @kernel_function(
        name="divide",
        description="첫 번째 숫자를 두 번째 숫자로 나눕니다",
    )
    def divide(self, number1: float, number2: float) -> str:
        """두 숫자의 나눗셈 결과를 반환합니다"""
        if number2 == 0:
            return "오류: 0으로 나눌 수 없습니다"
        result = number1 / number2
        return f"{number1} ÷ {number2} = {result:.4f}"

    @kernel_function(
        name="sqrt",
        description="숫자의 제곱근을 계산합니다",
    )
    def sqrt(self, number: float) -> str:
        """숫자의 제곱근을 반환합니다"""
        if number < 0:
            return "오류: 음수의 제곱근은 계산할 수 없습니다"
        result = math.sqrt(number)
        return f"√{number} = {result:.4f}"

    @kernel_function(
        name="power",
        description="base를 exponent 제곱한 값을 계산합니다",
    )
    def power(self, base: float, exponent: float) -> str:
        """거듭제곱을 반환합니다"""
        result = math.pow(base, exponent)
        return f"{base}^{exponent} = {result}"
