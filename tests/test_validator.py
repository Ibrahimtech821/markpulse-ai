import pandas as pd
from src.schemas.models import ColumnConfig, DatasetConfig
from src.services.validator import validate

CFG = DatasetConfig(max_total=30, columns=[
    ColumnConfig(name="Student_ID", role="id"),
    ColumnConfig(name="Quiz", role="assessment", max_marks=10),
    ColumnConfig(name="Midterm", role="assessment", max_marks=20),
    ColumnConfig(name="Total", role="total", max_marks=30),
])

def run(rows):
    df = pd.DataFrame(rows, dtype=str)
    clean, report = validate(df, CFG)
    return clean, {i.type.value for i in report.issues}

def test_absent_is_not_zero():
    clean, types = run({"Student_ID": ["1"], "Quiz": ["abs"], "Midterm": ["10"], "Total": ["10"]})
    assert pd.isna(clean.loc[0, "Quiz"])
    assert "missing_value" in types

def test_real_zero_stays_zero():
    clean, _ = run({"Student_ID": ["1"], "Quiz": ["0"], "Midterm": ["10"], "Total": ["10"]})
    assert clean.loc[0, "Quiz"] == 0

def test_out_of_range():
    _, types = run({"Student_ID": ["1"], "Quiz": ["5"], "Midterm": ["138"], "Total": ["143"]})
    assert "out_of_range" in types

def test_duplicate_id():
    _, types = run({"Student_ID": ["1", "1"], "Quiz": ["5", "6"], "Midterm": ["10", "10"], "Total": ["15", "16"]})
    assert "duplicate_id" in types

def test_blank_total_filled():
    clean, types = run({"Student_ID": ["1"], "Quiz": ["5"], "Midterm": ["10"], "Total": [""]})
    assert clean.loc[0, "Total"] == 15
    assert "total_filled" in types

def test_total_mismatch():
    _, types = run({"Student_ID": ["1"], "Quiz": ["5"], "Midterm": ["10"], "Total": ["20"]})
    assert "total_mismatch" in types