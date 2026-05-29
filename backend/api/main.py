from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.startups import router as startup_router

app = FastAPI(
    title="Startup Intelligence API",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(startup_router)

@app.get("/")
def root():
    return {
        "message": "Startup Intelligence API Running"
    }