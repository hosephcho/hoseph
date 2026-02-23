"""
데이터 분석 플러그인

Azure ML 환경에서 자주 사용되는 데이터 분석 관련 기능을 제공합니다.
실제 환경에서는 Azure ML Dataset, Blob Storage 연동을 추가할 수 있습니다.
"""

import json
import statistics
from typing import Annotated
from semantic_kernel.functions import kernel_function


class DataAnalysisPlugin:
    """데이터 통계 분석을 제공하는 플러그인"""

    @kernel_function(
        name="calculate_statistics",
        description="숫자 리스트의 기초 통계(평균, 중앙값, 표준편차, 최대/최솟값)를 계산합니다. "
                    "입력은 쉼표로 구분된 숫자 문자열입니다. 예: '1, 2, 3, 4, 5'",
    )
    def calculate_statistics(
        self,
        numbers: Annotated[str, "쉼표로 구분된 숫자 목록 (예: '10, 20, 30, 40, 50')"],
    ) -> str:
        """입력된 숫자 목록의 기초 통계를 계산합니다"""
        try:
            num_list = [float(n.strip()) for n in numbers.split(",") if n.strip()]
            if not num_list:
                return "오류: 유효한 숫자가 없습니다"

            result = {
                "count": len(num_list),
                "mean": round(statistics.mean(num_list), 4),
                "median": round(statistics.median(num_list), 4),
                "std_dev": round(statistics.stdev(num_list), 4) if len(num_list) > 1 else 0,
                "min": min(num_list),
                "max": max(num_list),
                "range": max(num_list) - min(num_list),
            }
            return json.dumps(result, ensure_ascii=False)
        except ValueError as e:
            return f"오류: 숫자 파싱 실패 - {str(e)}"

    @kernel_function(
        name="find_outliers",
        description="숫자 리스트에서 IQR 방법으로 이상값(outlier)을 탐지합니다. "
                    "입력은 쉼표로 구분된 숫자 문자열입니다.",
    )
    def find_outliers(
        self,
        numbers: Annotated[str, "쉼표로 구분된 숫자 목록"],
    ) -> str:
        """IQR 방법으로 이상값을 탐지합니다"""
        try:
            num_list = sorted([float(n.strip()) for n in numbers.split(",") if n.strip()])
            if len(num_list) < 4:
                return "이상값 탐지를 위해 최소 4개의 데이터가 필요합니다"

            n = len(num_list)
            q1 = num_list[n // 4]
            q3 = num_list[3 * n // 4]
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outliers = [x for x in num_list if x < lower_bound or x > upper_bound]

            result = {
                "Q1": q1,
                "Q3": q3,
                "IQR": iqr,
                "lower_bound": round(lower_bound, 4),
                "upper_bound": round(upper_bound, 4),
                "outliers": outliers,
                "outlier_count": len(outliers),
            }
            return json.dumps(result, ensure_ascii=False)
        except ValueError as e:
            return f"오류: {str(e)}"

    @kernel_function(
        name="compare_datasets",
        description="두 데이터셋의 평균을 비교하고 차이를 분석합니다. "
                    "각 데이터셋은 쉼표로 구분된 숫자 문자열입니다.",
    )
    def compare_datasets(
        self,
        dataset_a: Annotated[str, "첫 번째 데이터셋 (쉼표로 구분된 숫자)"],
        dataset_b: Annotated[str, "두 번째 데이터셋 (쉼표로 구분된 숫자)"],
    ) -> str:
        """두 데이터셋을 비교합니다"""
        try:
            list_a = [float(n.strip()) for n in dataset_a.split(",") if n.strip()]
            list_b = [float(n.strip()) for n in dataset_b.split(",") if n.strip()]

            mean_a = statistics.mean(list_a)
            mean_b = statistics.mean(list_b)
            diff = mean_a - mean_b
            pct_diff = (diff / mean_b * 100) if mean_b != 0 else 0

            result = {
                "dataset_a": {"count": len(list_a), "mean": round(mean_a, 4)},
                "dataset_b": {"count": len(list_b), "mean": round(mean_b, 4)},
                "mean_difference": round(diff, 4),
                "percentage_difference": f"{pct_diff:.2f}%",
                "larger_dataset": "A" if mean_a > mean_b else "B" if mean_b > mean_a else "동일",
            }
            return json.dumps(result, ensure_ascii=False)
        except ValueError as e:
            return f"오류: {str(e)}"
