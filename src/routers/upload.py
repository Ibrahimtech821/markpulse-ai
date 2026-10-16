import io
import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from src.schemas.models import DatasetConfig
from src.services.validator import validate
from src.services.stats_engine import compute_stats

router = APIRouter(prefix="/api", tags=["upload"])


async def load_inputs(file:UploadFile,config:str):
    try:
        cfg = DatasetConfig.model_validate_json(config)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    df = pd.read_csv(io.BytesIO(await file.read()), dtype=str)
    df.columns = [c.strip() for c in df.columns]
    
    missing = [c.name for c in cfg.columns if c.name not in df.columns]
    if missing:
        raise HTTPException(status_code=422, detail=f"Columns not in CSV: {missing}")
    return df,cfg


@router.post("/validate")
async def validate_upload(file: UploadFile , config: str = Form(...)):
    df,cfg=await load_inputs(file,config)
    clean, report = validate(df, cfg)
    clean = clean.astype(object).where(clean.notna(), None)

    return {
        "report": report.model_dump(),
        "clean_data": clean.to_dict("records"),
    }

@router.post("/stats")
async def stats_engine(file:UploadFile,config: str = Form(...)):
    df,cfg=await load_inputs(file,config)
    clean, report = validate(df, cfg)      # step 1: flag problems, convert to numbers
    stats = compute_stats(clean, cfg)      # step 2: math on the valid cells only
    return {"issues_count": len(report.issues), "stats": stats}