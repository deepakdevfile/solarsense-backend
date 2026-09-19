from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .schemas import AuthPayload, UserOut

app = FastAPI(title = "SolarSense API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/")
async def root():
    return {"message": "Hello from backend"}

@app.post("/auth/register", response_model=UserOut, status_code=201)
def register_user(payload: AuthPayload, db: Session = Depends(get_db)):
    print(payload)
    return payload