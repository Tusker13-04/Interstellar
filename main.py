from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import (
    import_export, 
    placement, 
    search_retrieve, 
    waste, 
    time_simulation, 
    logs, 
    dashboard, 
    visualization,
    llm_router  # NEW: Add LLM integration
)


app = FastAPI(
    title="Interstellar Cargo Management API",  # Updated title
    description="API for managing 3D cargo placement, retrieval, waste, time simulation, and LLM integration.",  # Updated description
    version="1.1.0"  # Updated version
)


# Add CORS middleware with proper configuration
app.add_middleware(
    CORSMiddleware,
    # Allow specific origins with proper protocol
    allow_origins=["*"],  # Allow all origins for development
        # "http://localhost:3000",
        # "http://127.0.0.1:3000",
        # "http://host.docker.internal:3000",
        # "http://0.0.0.0:3000"
        # Add your frontend domain if deployed
        #allow all origins for development on port 3000


    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Expose headers to the browser
)


# Include all existing routers
app.include_router(import_export.router)
app.include_router(logs.router)
app.include_router(placement.router)
app.include_router(search_retrieve.router)
app.include_router(waste.router)
app.include_router(time_simulation.router)
app.include_router(dashboard.router)
app.include_router(visualization.router)

# NEW: Include LLM integration router
app.include_router(llm_router.router)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Interstellar Cargo Management API is running!",
        "version": "1.1.0",
        "features": [
            "3D Bin Packing",
            "Cargo Placement & Retrieval", 
            "Waste Management",
            "Time Simulation",
            "Dashboard & Visualization",
            "LLM Integration"  # NEW feature
        ],
        "llm_endpoints": [
            "/api/llm/chat",
            "/api/llm/health", 
            "/api/llm/generate-sample-data",
            "/api/llm/cargo"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Interstellar Cargo Management System")
    print("📡 Features: 3D Bin Packing + LLM Integration")
    print("🔧 Make sure Ollama is running: ollama serve")
    print("📍 API will be available at: http://localhost:8000")
    print("🤖 LLM Chat endpoint: http://localhost:8000/api/llm/chat")
    uvicorn.run(app, host="0.0.0.0", port=8000)
