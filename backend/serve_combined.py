import os
import sys

sys.path.insert(0, os.path.dirname(__file__))  # adds backend/ to path

from fastapi.staticfiles import StaticFiles
from app import app  # now works because backend/ is on the path

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "dist")

if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:
    print("WARNING: dist/ not found.")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)