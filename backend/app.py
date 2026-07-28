import os
from typing import Dict, List, Any

import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from scheduler import ScheduleMaker

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


# ── Pydantic Request Models ─────────────────────────────
class PreferenceLevels(BaseModel):
    high: List[int] = []
    mid: List[int] = []
    low: List[int] = []


class ScheduleRequest(BaseModel):
    start: str
    end: str
    forced: List[int]
    sun_quotas: Dict[str, int]
    prefs: Dict[str, PreferenceLevels]  # Guarantees inner elements are integers
    targets: Dict[str, int]
    fixed_holidays: List[int]
    fixed_holiday_quotas: Dict[str, int]


# ── Helper Functions ────────────────────────────────────
def clean_schedule(final_sched: Dict[str, Any]) -> Dict[str, List[int]]:
    cleaned = {}
    for k, v in final_sched.items():
        if isinstance(v, np.ndarray):
            v = v.tolist()
        cleaned[k] = [int(x) for x in v]
    return cleaned


# ── Endpoints ───────────────────────────────────────────
@app.post("/api/schedule")
@app.post("/api/schedule")
def create(req: ScheduleRequest):

    prefs_dict = {
        worker: levels.model_dump()
        for worker, levels in req.prefs.items()
    }

    with open("debug_api.txt", "w") as f:
        f.write(str({
            "start": req.start,
            "end": req.end,
            "forced": req.forced,
            "prefs": prefs_dict,
            "targets": req.targets,
            "fixed_holidays": req.fixed_holidays,
            "fixed_holiday_quotas": req.fixed_holiday_quotas
        }))

    maker = ScheduleMaker()

    schedule, num_days = maker.generate(
        start_date=req.start,
        end_date=req.end,
        forced_days=req.forced,
        sunday_quotas=req.sun_quotas,
        prefs=prefs_dict,
        targets=req.targets,
        fixed_holidays=req.fixed_holidays,
        fixed_holidays_quotas=req.fixed_holiday_quotas,
    )

    return {
        "schedule": clean_schedule(schedule),
        "num_days": num_days,
        "table": maker.to_dataframe().to_dict(orient="records"),
    }

# ── Serve React Frontend ────────────────────────────────
if os.path.exists("dist"):
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        return FileResponse("dist/index.html")