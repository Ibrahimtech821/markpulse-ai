import pandas as pd
from src.schemas.models import (
    ColumnRole, DatasetConfig, Issue, IssueType, ValidationReport,
)
import numpy as np
from scipy import stats as sp

def _num(x):
    return None if pd.isna(x) else round(float(x),2)
def valid_stats(series,max_marks):
    n_missing=int(series.isna().sum())
    out_range=(series<0 ) | ( series > 100)
    n_out_range=int(out_range.sum())
    valid= series[(series>0) & (series <= max_marks)]
    percents=valid / max_marks *100
    return percents, n_out_range,n_missing

def basic_stats(percents):
    return {
        "n":len(percents),
        "mean":_num(percents.mean()),
        "median":_num(percents.median()),
        "std":_num(percents.std()),
    }
def modal_bin(percents):
    if len(percents)==0:
        return None
    count,edges=np.histogram(percents,bins=list(range(0,101,10)))
    i=int(np.argmax(count))
    return f"{edges[i]} - {edges[i+1]}"
def describe_column(series, max_marks, pass_percent, ids):
    """All stats for one column. Returns (stats dict, valid percents)."""
    percents, n_missing, n_bad = valid_stats(series, max_marks)
    n = len(percents)

    q1 = percents.quantile(0.25)
    q3 = percents.quantile(0.75)
    iqr = q3 - q1
    outliers = percents[(percents < q1 - 1.5 * iqr) | (percents > q3 + 1.5 * iqr)]

    stats = basic_stats(percents)
    stats["mode_bin"] = modal_bin(percents)
    stats["q1"] = _num(q1)
    stats["q3"] = _num(q3)
    stats["iqr"] = _num(iqr)
    stats["skewness"] = _num(sp.skew(percents)) if n >= 3 else None
    stats["kurtosis"] = _num(sp.kurtosis(percents)) if n >= 4 else None
    stats["pass_rate"] = _num((percents >= pass_percent).mean() * 100) if n else None
    stats["outlier_count"] = len(outliers)
    stats["outlier_ids"] = ids[outliers.index].tolist()
    stats["excluded_missing"] = n_missing
    stats["excluded_out_of_range"] = n_bad
    return stats, percents

def compute_stats(df,config:DatasetConfig):
    id_col = next(c.name for c in config.columns if c.role == ColumnRole.ID)
    total_cfg = next((c for c in config.columns if c.role == ColumnRole.TOTAL), None)
    ids = df[id_col].astype(str).str.strip()
    columns = {}
    percent_table = {}  # valid % per assessment, used for correlations

    for cfg in config.columns:
        if cfg.role != ColumnRole.ASSESSMENT:
            continue
        stats, percents = describe_column(df[cfg.name], cfg.max_marks, config.pass_percent, ids)
        columns[cfg.name] = stats
        percent_table[cfg.name] = percents

    if total_cfg:
        stats, _ = describe_column(df[total_cfg.name], config.max_total, config.pass_percent, ids)
        columns["Total"] = stats

    corr = pd.DataFrame(percent_table).corr()  # ignores missing cells pairwise
    correlations={}
    for a in corr.index:
        correlations[a]={}
        for b in corr.columns:
            corr[a][b]=_num(corr.loc[a,b])

    return {"columns": columns, "correlations": correlations}
