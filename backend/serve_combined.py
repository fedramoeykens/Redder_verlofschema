import os
from fastapi.staticfiles import StaticFiles

from app import app  # your unmodified app.py

app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/"]

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:
    print(f"WARNING: no build found at {FRONTEND_DIST} — run `npm run build` from the project root first.")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)