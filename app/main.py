from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any

app = FastAPI(title = "SolarSense API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AuthPayload(BaseModel):
    email: str
    password: str

@app.get("/")
async def root():
    return {"message": "Hello from backend"}
