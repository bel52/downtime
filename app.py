from fastapi import FastAPI
from api.endpoints import router
from scheduler import start_scheduler  # Import the modified scheduler logic

app = FastAPI()

# Include all API endpoints
app.include_router(router)

@app.on_event("startup")
async def startup_event():
    start_scheduler()  # Ensures the scheduler starts only if it is not already running
    print("Scheduler started and application is running.")
