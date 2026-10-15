from enum import Enum
from pydantic import BaseModel, Field

class ColumnRole(str,Enum):
    ASSESSMENT="assessment" #quiz,midterm,fina;
    EARNEDBONUS="earnedbonus" #project bonus
    TOTAL = "total"                # reported Total column
    ID = "id" 
class ColumnConfig(BaseModel):
    name:str
    role:ColumnRole
    max_marks:float | None=Field(default=None,gt=0)
class IssueType(str,Enum):
    DUPLICATE_ID = "duplicate_id"
    OUT_OF_RANGE = "out_of_range"        # e.g. 138 instead of 13.8
    MISSING_VALUE = "missing_value"      # blank = absent, NOT zero
    TOTAL_MISMATCH = "total_mismatch"    # row sum != reported Total
    TOTAL_FILLED = "total_filled"        # blank Total computed by Python
class Issue(BaseModel):
    type: IssueType
    row: int
    column: str | None = None
    student_id: str | None = None
    message: str

class DatasetConfig(BaseModel):
    max_total: float = Field(gt=0 , le=100)             # e.g. 70
    pass_percent: float = Field(default=50, ge=0, le=100)
    columns: list[ColumnConfig]


class ValidationReport(BaseModel):
    rows: int
    issues: list[Issue]

