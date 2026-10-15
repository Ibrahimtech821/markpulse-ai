import pandas as pd
from src.schemas.models import (
    ColumnRole, DatasetConfig, Issue, IssueType, ValidationReport,)

MISSING_TOKENS = {"", "na", "n/a", "null", "none", "nan", "abs", "absent", "ex", "excused", "-"}


def validate(df_raw: pd.DataFrame, config: DatasetConfig):
    """Returns (clean_df, ValidationReport). Never fixes values silently."""
    df = df_raw.copy()
    df.columns = [c.strip() for c in df.columns]
    issues: list[Issue] = []

    id_col = next(c.name for c in config.columns if c.role == ColumnRole.ID)
    total_cfg = next((c for c in config.columns if c.role == ColumnRole.TOTAL), None)
    part_cfgs = [c for c in config.columns
                 if c.role in (ColumnRole.ASSESSMENT, ColumnRole.EARNEDBONUS)]

    # 1. duplicate IDs
    ids = df[id_col].astype(str).str.strip()
    for i in df.index[ids.duplicated(keep=False)]:
        issues.append(Issue(type=IssueType.DUPLICATE_ID, row=int(i) + 2, column=id_col,
                            student_id=ids[i], message=f"ID '{ids[i]}' appears more than once"))

    # 2. numeric conversion: blank/absent stays NaN (never 0)
    for cfg in part_cfgs + ([total_cfg] if total_cfg else []):
        s = df[cfg.name].astype(str).str.strip()
        is_missing = df[cfg.name].isna() | s.str.lower().isin(MISSING_TOKENS)
        num = pd.to_numeric(s.where(~is_missing), errors="coerce")
        bad = ~is_missing & num.isna()
        df[cfg.name] = num

        for i in df.index:
            sid, row = ids[i], int(i) + 2
            if (is_missing[i] or bad[i]) and cfg.role != ColumnRole.TOTAL:
                why = "non-numeric, treated as missing" if bad[i] else "blank/absent, kept as missing (not 0)"
                issues.append(Issue(type=IssueType.MISSING_VALUE, row=row, column=cfg.name,
                                    student_id=sid, message=why))
            elif cfg.max_marks and not pd.isna(num[i]) and not (0 <= num[i] <= cfg.max_marks):
                issues.append(Issue(type=IssueType.OUT_OF_RANGE, row=row, column=cfg.name,
                                    student_id=sid,
                                    message=f"{num[i]} is outside 0-{cfg.max_marks}"))

    # 3. row-sum check against reported Total
    if total_cfg:
        computed = df[[c.name for c in part_cfgs]].sum(axis=1, min_count=1)
        for i in df.index:
            sid, row = ids[i], int(i) + 2
            reported = df.at[i, total_cfg.name]
            if pd.isna(reported):
                df.at[i, total_cfg.name] = computed[i]
                issues.append(Issue(type=IssueType.TOTAL_FILLED, row=row, column=total_cfg.name,
                                    student_id=sid, message=f"Blank Total filled with {computed[i]}"))
            elif abs(reported - computed[i]) > 0.01:
                issues.append(Issue(type=IssueType.TOTAL_MISMATCH, row=row, column=total_cfg.name,
                                    student_id=sid,
                                    message=f"Reported {reported} but columns sum to {computed[i]}"))

    return df, ValidationReport(rows=len(df), issues=issues)