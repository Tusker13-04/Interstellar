from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd
import json
from typing import Optional, Dict, Any, List
import requests
from datetime import datetime, timedelta
import re
import sys
import os

router = APIRouter(prefix="/api/llm", tags=["LLM Integration"])

# Ollama configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.1"  # or "mistral", "llama2", etc.

# Try to import your placement system
try:
    from placement_algo import AdvancedCargoPlacement
    PLACEMENT_SYSTEM_AVAILABLE = True
    print("✅ Successfully imported AdvancedCargoPlacement")
except ImportError as e:
    print(f"⚠️  Could not import placement system: {e}")
    PLACEMENT_SYSTEM_AVAILABLE = False

# Initialize placement system
placement_system = None
if PLACEMENT_SYSTEM_AVAILABLE:
    container_dims = {"width": 10, "depth": 10, "height": 10}
    placement_system = AdvancedCargoPlacement(container_dims)
    print("✅ Initialized AdvancedCargoPlacement system")

# Load cargo data
try:
    cargo_df = pd.read_csv("cargo_data.csv")
    print(f"✅ Loaded {len(cargo_df)} cargo items from CSV")
except FileNotFoundError:
    print("⚠️  cargo_data.csv not found, will create sample data")
    # Create sample data
    sample_data = [
        {'id': 'C001', 'name': 'Medical Kit', 'category': 'Medical', 'position': 'Bay A-1', 
         'mass': 15.5, 'coordinates_x': 0, 'coordinates_y': 0, 'coordinates_z': 0,
         'accessibility_score': 0.85, 'temperature_sensitive': True, 'priority': 80},
        {'id': 'C002', 'name': 'Food Supplies', 'category': 'Food', 'position': 'Bay B-2', 
         'mass': 45.2, 'coordinates_x': 2, 'coordinates_y': 1, 'coordinates_z': 0,
         'accessibility_score': 0.75, 'temperature_sensitive': True, 'priority': 60}
    ]
    cargo_df = pd.DataFrame(sample_data)
    cargo_df.to_csv("cargo_data.csv", index=False)

# ============= LLM INTEGRATION FUNCTIONS =============

def get_cargo_info(cargo_id: Optional[str] = None) -> Dict[str, Any]:
    """Get information about cargo items"""
    if cargo_id:
        cargo = cargo_df[cargo_df['id'].astype(str) == str(cargo_id)]
        if cargo.empty:
            return {"error": f"Cargo {cargo_id} not found"}
        return {"status": "success", "data": cargo.to_dict('records')[0]}
    else:
        return {
            "status": "success",
            "total_items": len(cargo_df),
            "data": cargo_df.to_dict('records')
        }

def get_3d_coordinates(cargo_id: str) -> Dict[str, Any]:
    """Get 3D coordinates and spatial info for a specific cargo item"""
    cargo = cargo_df[cargo_df['id'].astype(str) == str(cargo_id)]
    if cargo.empty:
        return {"error": f"Cargo {cargo_id} not found"}

    item = cargo.iloc[0]
    return {
        "status": "success",
        "cargo_id": cargo_id,
        "name": item.get('name', 'Unknown'),
        "coordinates_3d": {
            "x": float(item.get('coordinates_x', 0)),
            "y": float(item.get('coordinates_y', 0)),
            "z": float(item.get('coordinates_z', 0))
        },
        "dimensions": item.get('dimensions', '1x1x1'),
        "volume": float(item.get('volume', 1.0)) if 'volume' in item else 1.0,
        "accessibility_score": float(item.get('accessibility_score', 0.5)),
        "position": item.get('position', 'Unknown'),
        "category": item.get('category', 'General'),
        "priority": int(item.get('priority', 1))
    }

def run_bin_packing_optimization() -> Dict[str, Any]:
    """Run 3D bin packing optimization using your placement system"""
    global cargo_df, placement_system

    if not PLACEMENT_SYSTEM_AVAILABLE or not placement_system:
        return {
            "status": "error", 
            "message": "Placement system not available. Make sure placement_algo.py is in the same directory."
        }

    try:
        # Run optimization using your placement system
        result = placement_system.run_optimization_for_llm()

        # Reload updated CSV data
        if os.path.exists("cargo_data.csv"):
            cargo_df = pd.read_csv("cargo_data.csv")

        return result

    except Exception as e:
        return {
            "status": "error", 
            "message": f"Optimization failed: {str(e)}"
        }

def get_container_utilization() -> Dict[str, Any]:
    """Get space utilization statistics"""
    global placement_system

    if not PLACEMENT_SYSTEM_AVAILABLE or not placement_system:
        # Fallback calculation from CSV data
        if 'volume' in cargo_df.columns:
            total_volume = 1000  # Default container volume
            used_volume = cargo_df['volume'].sum()
            return {
                "status": "success",
                "utilization_percentage": round((used_volume / total_volume) * 100, 2),
                "total_items": len(cargo_df),
                "total_volume": total_volume,
                "used_volume": used_volume
            }
        return {"error": "Placement system not available"}

    try:
        return placement_system.get_container_utilization_stats()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def simulate_item_retrieval(cargo_id: str) -> Dict[str, Any]:
    """Simulate retrieving a specific item"""
    global placement_system

    if not PLACEMENT_SYSTEM_AVAILABLE or not placement_system:
        # Fallback simulation
        cargo = cargo_df[cargo_df['id'].astype(str) == str(cargo_id)]
        if cargo.empty:
            return {"error": f"Cargo {cargo_id} not found"}

        item = cargo.iloc[0]
        return {
            "status": "success",
            "target_item": cargo_id,
            "accessibility_score": float(item.get('accessibility_score', 0.5)),
            "estimated_retrieval_time_minutes": 5,
            "blocking_items_count": 0,
            "retrieval_difficulty": "Easy" if item.get('accessibility_score', 0.5) > 0.8 else "Medium"
        }

    try:
        return placement_system.simulate_item_retrieval_for_llm(cargo_id)
    except Exception as e:
        return {"status": "error", "message": str(e)}

def generate_new_cargo_data() -> Dict[str, Any]:
    """Generate new cargo data using the placement system"""
    global cargo_df, placement_system

    if not PLACEMENT_SYSTEM_AVAILABLE or not placement_system:
        return {"error": "Placement system not available"}

    try:
        # Create some sample items to place
        test_items = [
            {'itemId': 'ITEM001', 'width': 2, 'depth': 2, 'height': 2, 'mass': 15.5, 'priority': 80},
            {'itemId': 'ITEM002', 'width': 3, 'depth': 2, 'height': 1, 'mass': 45.2, 'priority': 60},
            {'itemId': 'ITEM003', 'width': 1, 'depth': 1, 'height': 3, 'mass': 120.0, 'priority': 40},
            {'itemId': 'ITEM004', 'width': 2, 'depth': 3, 'height': 1, 'mass': 8.3, 'priority': 70},
            {'itemId': 'ITEM005', 'width': 1, 'depth': 2, 'height': 2, 'mass': 67.8, 'priority': 30}
        ]

        # Run placement algorithm
        placements, _ = placement_system.find_optimal_placement(test_items)

        # Export to CSV
        df = placement_system.export_cargo_data_for_llm()
        cargo_df = df  # Update global cargo_df

        return {
            "status": "success",
            "message": f"Generated and placed {len(placements)} items",
            "items_placed": len(placements),
            "csv_file": "cargo_data.csv"
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

# Map function names to actual functions
AVAILABLE_FUNCTIONS = {
    "get_cargo_info": get_cargo_info,
    "get_3d_coordinates": get_3d_coordinates,
    "run_bin_packing_optimization": run_bin_packing_optimization,
    "get_container_utilization": get_container_utilization,
    "simulate_item_retrieval": simulate_item_retrieval,
    "generate_new_cargo_data": generate_new_cargo_data
}

# ============= OLLAMA LLM INTEGRATION =============

def call_ollama(prompt: str, system_prompt: str = "") -> str:
    """Call Ollama API"""
    try:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": full_prompt,
                "stream": False,
                "temperature": 0.7
            },
            timeout=60
        )

        if response.status_code == 200:
            return response.json()["response"]
        else:
            return f"Error calling Ollama: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

def parse_function_call(llm_response: str) -> Optional[Dict[str, Any]]:
    """Parse function calls from LLM response"""
    # Look for function call pattern
    pattern = r'(\w+)\((.*?)\)'
    matches = re.findall(pattern, llm_response)

    for func_name, args_str in matches:
        if func_name in AVAILABLE_FUNCTIONS:
            args = {}
            if args_str.strip():
                for arg in args_str.split(','):
                    if '=' in arg:
                        key, value = arg.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        try:
                            if value.lower() == 'true':
                                value = True
                            elif value.lower() == 'false':
                                value = False
                            elif value.replace('.', '').replace('-', '').isdigit():
                                value = float(value) if '.' in value else int(value)
                        except:
                            pass
                        args[key] = value
            return {"function": func_name, "arguments": args}
    return None

# ============= API MODELS =============

class ChatMessage(BaseModel):
    message: str
    conversation_history: Optional[List[Dict]] = []

# ============= API ENDPOINTS =============

@router.post("/chat")
async def chat_with_llm(chat: ChatMessage):
    """Handle chat requests with Ollama LLM for cargo management"""
    try:
        # Build system prompt
        system_prompt = f"""You are an AI assistant for the Interstellar 3D cargo management system.
You help astronauts query cargo information, manage 3D bin packing, and optimize space utilization.

CURRENT CARGO DATA:
- Total items: {len(cargo_df)}
- Columns: {', '.join(cargo_df.columns.tolist())}
- 3D Placement System: {"Available" if PLACEMENT_SYSTEM_AVAILABLE else "Not Available"}

AVAILABLE FUNCTIONS (call them when needed):
1. get_cargo_info(cargo_id=None) - Get all cargo or specific item info
2. get_3d_coordinates(cargo_id="C001") - Get 3D position and spatial info
3. run_bin_packing_optimization() - Run 3D optimization algorithms  
4. get_container_utilization() - Get space utilization analysis
5. simulate_item_retrieval(cargo_id="C001") - Simulate retrieving an item
6. generate_new_cargo_data() - Generate new cargo using 3D placement system

TO CALL A FUNCTION: Write it exactly like: get_3d_coordinates(cargo_id="C001")

Be helpful and provide clear information about cargo locations, 3D positioning, and optimization suggestions."""

        # Get LLM response
        llm_response = call_ollama(chat.message, system_prompt)

        # Check if LLM wants to call a function
        function_call = parse_function_call(llm_response)

        if function_call:
            func_name = function_call["function"]
            func_args = function_call["arguments"]

            # Execute function
            function_result = AVAILABLE_FUNCTIONS[func_name](**func_args)

            # Get final response with function result
            follow_up_prompt = f"""The function {func_name} was called with arguments {func_args}.

Function result:
{json.dumps(function_result, indent=2)}

Based on this result, provide a helpful response to the user's question: "{chat.message}"

Be concise and format the information clearly. Focus on 3D coordinates when available."""

            final_response = call_ollama(follow_up_prompt, system_prompt)

            return {
                "response": final_response,
                "function_called": func_name,
                "function_arguments": func_args,
                "function_result": function_result
            }

        # No function call, return direct response
        return {
            "response": llm_response,
            "function_called": None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def llm_health_check():
    """Check LLM system health"""
    health_status = {
        "status": "healthy",
        "ollama_running": False,
        "placement_system": PLACEMENT_SYSTEM_AVAILABLE,
        "cargo_items": len(cargo_df),
        "timestamp": datetime.now().isoformat()
    }

    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            health_status.update({
                "ollama_running": True,
                "available_models": [m["name"] for m in models],
                "current_model": MODEL_NAME
            })
    except:
        health_status["message"] = "Ollama not running. Start it with: ollama serve"

    return health_status

@router.post("/generate-sample-data")
async def create_sample_data():
    """Generate sample cargo data using placement system"""
    return generate_new_cargo_data()

@router.get("/cargo")
async def get_all_cargo():
    """Get all cargo data"""
    return cargo_df.to_dict('records')

@router.post("/reload-data")
async def reload_cargo_data():
    """Reload CSV data"""
    global cargo_df
    try:
        cargo_df = pd.read_csv("cargo_data.csv")
        return {"message": "Data reloaded", "items": len(cargo_df)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reloading data: {str(e)}")
