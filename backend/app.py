from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, List, Any
from scheduler import ScheduleMaker
import numpy as np
import pandas as pd
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def root():
    return {"message": "API is running"}

class Request(BaseModel):
    start: str
    end: str
    forced: List[int]
    sun_quotas: Dict[str, int]
    prefs: Dict[str, Any]
    targets: Dict[str, int]
    fixed_holidays: List[int]
    fixed_holiday_quotas: Dict[str, int]

def clean_schedule(final_sched):
    cleaned = {}
    for k, v in final_sched.items():
        if isinstance(v, np.ndarray):
            v = v.tolist()
        cleaned[k] = [int(x) for x in v]
    return cleaned

@app.post("/api/schedule")
def create(req: Request):
    maker = ScheduleMaker()
    maker.generate(
        req.start,
        req.end,
        req.forced,
        req.sun_quotas,
        req.prefs,
        req.targets,
        req.fixed_holidays,
        req.fixed_holiday_quotas,
    )
    return {"table": maker.to_dataframe().to_dict(orient="records")}

# ── Serve React frontend ────────────────────────────────
if os.path.exists("dist"):
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        return FileResponse("dist/index.html")