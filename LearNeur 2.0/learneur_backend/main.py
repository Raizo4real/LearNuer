from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import models
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import engine
from routers import auth_router
from routers import parent_router
from routers import game_router
from routers import analytics_router
from routers import settings
from routers import owner_router
from routers import doctor_router
from routers import chat_router
from routers import forum_router
from fastapi.staticfiles import StaticFiles

# 1. Initialize the Database
# This automatically creates all tables defined in models.py inside learneur.db
models.Base.metadata.create_all(bind=engine)

# 2. Initialize the FastAPI Application
app = FastAPI(
    title="LearNeur API",
    description="Backend API for the LearNeur platform handling auth, telemetry, and reporting.",
    version="1.0.0"
)

# 3. Configure CORS Middleware
# Allows the frontend HTML/JS to communicate with this backend.
# Added common local development ports (e.g., VS Code Live Server runs on 5500).
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:3000",
    "http://127.0.0.1",
    "http://127.0.0.1:5500",
    "https://learneur-eight.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # السطر ده بيفتح الأمان مؤقتاً لأي بورت فرونت إند بيكلمه
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
# 4. Include the Routers
app.include_router(auth_router.router)
app.include_router(parent_router.router)
app.include_router(game_router.router)
app.include_router(analytics_router.router)
app.include_router(settings.router)
app.include_router(owner_router.router)
app.include_router(doctor_router.router)
app.include_router(chat_router.router)
app.include_router(forum_router.router)
# 5. Root Health Check Endpoint
@app.get("/")
def read_root():
    return {
        "status": "Online", 
        "platform": "LearNeur API", 
        "message": "Database and Auth systems are actively running."
    }
