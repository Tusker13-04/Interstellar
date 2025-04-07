from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import import_export, placement, search_retrieve, waste, time_simulation, logs, dashboard, visualization

app = FastAPI(
    title="Cargo Management API",
    description="API for managing cargo placement, retrieval, waste, and time simulation.",
    version="1.0.0"
)

# Add CORS middleware with proper configuration
app.add_middleware(
    CORSMiddleware,
    # Allow specific origins with proper protocol
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://host.docker.internal:3000",
        "http://0.0.0.0:3000"
        # Add your frontend domain if deployed
        #allow all origins for development on port 3000
    ],
    
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Expose headers to the browser
)

app.include_router(import_export.router)
app.include_router(logs.router)
app.include_router(placement.router)
app.include_router(search_retrieve.router)
app.include_router(waste.router)
app.include_router(time_simulation.router)
app.include_router(dashboard.router)
app.include_router(visualization.router)


# Root endpoint
@app.get("/")
async def root():
    return {"message": "Cargo Management API is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)