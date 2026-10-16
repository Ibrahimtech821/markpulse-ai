import pandas as pd
from src.schemas.models import (
    ColumnRole, DatasetConfig, Issue, IssueType, ValidationReport,
)

MISSING_TOKENS = {"", "na", "n/a", "null", "none", "nan", "abs", "absent", "ex", "excused", "-"}


def _issue(kind, i, ids, column, message):
    """Build one Issue. i = table index, +2 gives the CSV line number."""
    return Issue(type=kind, row=int(i) + 2, column=column,
                 student_id=ids[i], message=message)


def _check_duplicates(ids, id_col):
    return [
        _issue(IssueType.DUPLICATE_ID, i, ids, id_col, f"ID '{ids[i]}' appears more than once")
        for i in ids.index[ids.duplicated(keep=False)]
    ]


def _check_column(df, cfg, ids):
    """Convert one column to numbers (blank/absent -> NaN, never 0) and flag problems."""
    text = df[cfg.name].astype(str).str.strip()
    missing = df[cfg.name].isna() | text.str.lower().isin(MISSING_TOKENS)
    nums = pd.to_numeric(text.where(~missing), errors="coerce")
    unreadable = ~missing & nums.isna()
    df[cfg.name] = nums

    issues = []
    if cfg.role != ColumnRole.TOTAL:  # blank Totals are handled in _check_totals
        for i in nums.index[missing | unreadable]:
            why = ("non-numeric, treated as missing" if unreadable[i]
                   else "blank/absent, kept as missing (not 0)")
            issues.append(_issue(IssueType.MISSING_VALUE, i, ids, cfg.name, why))

    if cfg.max_marks:
        out_of_range = (nums < 0) | (nums > cfg.max_marks)  # NaN compares False
        for i in nums.index[out_of_range]:
            issues.append(_issue(IssueType.OUT_OF_RANGE, i, ids, cfg.name,
                                 f"{nums[i]} is outside 0-{cfg.max_marks}"))
    return issues


def _check_totals(df, part_cols, total_col, ids):
    """Fill blank Totals and flag rows where reported Total != sum of parts."""
    computed = df[part_cols].sum(axis=1, min_count=1)
    reported = df[total_col].copy()
    issues = []

    for i in reported.index[reported.isna()]:
        df.at[i, total_col] = computed[i]
        issues.append(_issue(IssueType.TOTAL_FILLED, i, ids, total_col,
                             f"Blank Total filled with {computed[i]}"))

    mismatch = (reported - computed).abs() > 0.01
    for i in reported.index[mismatch]:
        issues.append(_issue(IssueType.TOTAL_MISMATCH, i, ids, total_col,
                             f"Reported {reported[i]} but columns sum to {computed[i]}"))
    return issues


def validate(df_raw: pd.DataFrame, config: DatasetConfig):
    """Returns (clean_df, ValidationReport). Never fixes values silently."""
    df = df_raw.copy()
    df.columns = [c.strip() for c in df.columns]

    id_col = next(c.name for c in config.columns if c.role == ColumnRole.ID)
    total_cfg = next((c for c in config.columns if c.role == ColumnRole.TOTAL), None)
    part_cfgs = [c for c in config.columns
                 if c.role in (ColumnRole.ASSESSMENT, ColumnRole.EARNEDBONUS)]

    ids = df[id_col].astype(str).str.strip()

    # columns we need to check: the parts, plus Total if it exists
    cols_to_check = list(part_cfgs)
    if total_cfg:
        cols_to_check.append(total_cfg)

    # step 1: duplicate IDs
    issues = _check_duplicates(ids, id_col)

    # step 2: check each column
    for cfg in cols_to_check:
        issues += _check_column(df, cfg, ids)

    # step 3: Total vs sum of parts
    if total_cfg:
        part_names = [c.name for c in part_cfgs]
        issues += _check_totals(df, part_names, total_cfg.name, ids)

    return df, ValidationReport(rows=len(df), issues=issues)