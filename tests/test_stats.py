import pandas as pd
import pytest
from src.schemas.models import ColumnConfig, DatasetConfig
from src.services.stats_engine import compute_stats


def make(marks, max_marks):
    df = pd.DataFrame({"Student_ID": [str(i + 1) for i in range(len(marks))],
                       "Midterm": marks})
    cfg = DatasetConfig(max_total=max_marks, columns=[
        ColumnConfig(name="Student_ID", role="id"),
        ColumnConfig(name="Midterm", role="assessment", max_marks=max_marks),
    ])
    return compute_stats(df, cfg)["columns"]["Midterm"]


def test_basic_numbers():
    s = make([8, 12, 14, 16, 20], 20)   # = 40, 60, 70, 80, 100 %
    assert s["mean"] == 70 and s["median"] == 70
    assert s["std"] == pytest.approx(22.36)
    assert s["q1"] == 60 and s["q3"] == 80 and s["iqr"] == 20
    assert s["pass_rate"] == 80          # 40% fails, the other 4 pass
    assert s["skewness"] == 0
    assert s["kurtosis"] == pytest.approx(-0.95)
    assert s["outlier_count"] == 0


def test_missing_and_bad_are_excluded():
    s = make([10, 12, 138, 14, None], 20)
    assert s["n"] == 3
    assert s["mean"] == 60
    assert s["excluded_missing"] == 1
    assert s["excluded_out_of_range"] == 1


def test_outlier_found():
    s = make([50, 52, 54, 56, 58, 100], 100)
    assert s["outlier_count"] == 1
    assert s["outlier_ids"] == ["6"]