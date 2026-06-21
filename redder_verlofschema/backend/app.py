from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any

from scheduler import ScheduleMaker   # your existing module
maker = ScheduleMaker()
app = FastAPI()
@app.get("/")
def root():
    return {"message": "API is running"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Request(BaseModel):
    start: str
    end: str

    forced: List[int]

    sun_quotas: Dict[str, int]
    prefs: Dict[str, Any]
    targets: Dict[str, int]

    fixed_holidays: List[int]
    fixed_holiday_quotas: Dict[str, int]

import numpy as np

def clean_schedule(final_sched):
    cleaned = {}

    for k, v in final_sched.items():

        # convert numpy → python list
        if isinstance(v, np.ndarray):
            v = v.tolist()

        # ensure integers
        v = [int(x) for x in v]

        cleaned[k] = v

    return cleaned
@app.post("/schedule")

def create(req: Request):
    print('creating schedule with request:', req  )
    final_sched, d_count = maker.generate(
        req.start,
        req.end,
        req.forced,
        req.sun_quotas,
        req.prefs,
        req.targets,
        req.fixed_holidays,
        req.fixed_holiday_quotas
    )
    print("SCHEDULE:", final_sched)
    return {
        "schedule": clean_schedule(final_sched),
        "counts": d_count
    }
    