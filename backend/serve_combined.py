import os
from fastapi.staticfiles import StaticFiles
from app import app  # your unmodified app.py

app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/"]

FRONTEND_DIST = os.path.join(os.getcwd(), "dist")

if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:
    print("WARNING: dist folder not found. React build missing.")
    
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)