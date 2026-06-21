import os
from fastapi.staticfiles import StaticFiles
from app import app

# dist/ is built at repo root, we're running from backend/
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "dist")

if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:
    print("WARNING: dist/ not found.")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)