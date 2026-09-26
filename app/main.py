from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db import Base, engine
from app.routers import users
from app.routers import installations
from app.routers import measurements
from app.routers import weathers
from app.config import settings

# Base.metadata.create_all(bind=engine)
app = FastAPI(title = "SolarSense API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(installations.router)
app.include_router(measurements.router)
app.include_router(weathers.router)

@app.get("/")
async def root():
    return {"message": "Hello from backend"}