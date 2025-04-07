import json
import re
import csv
import os
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
import polars as pl
from datetime import datetime
from schemas import Position, ReturnPlanRequest, ReturnPlanResponse, ReturnItem, ReturnPlanStep, RetrievalStep, CompleteUndockingRequest, Object3D, ReturnManifest
import httpx
from algos.search_algo import ItemSearchSystem
from algos.waste_algo import (
    load_waste_items,
    load_imported_items,
    link_waste_with_imported_items,
    select_waste_items_greedy,
    generate_return_plan as generate_return_plan_steps,
    create_return_manifest
)

router = APIRouter(
    prefix="/api/waste",
    tags=["waste"],
)

async def search_retrieve(itemId: int, zone: str) -> dict:
    """Call the search endpoint to get retrieval steps for an item."""
    print(f"\nCalling search endpoint for item {itemId} in zone {zone}")
    async with httpx.AsyncClient() as client:
        try:
            # First, check if the item exists in the cargo arrangement data
            cargo_df = pl.read_csv("cargo_arrangement.csv")
            # Convert itemId to string for comparison
            item_data = cargo_df.filter(pl.col("itemId").cast(str) == str(itemId)).to_dicts()
            
            if not item_data:
                print(f"Item {itemId} not found in cargo arrangement data")
                return {"success": False, "found": False, "retrieval_steps": []}
            
            # Get the container ID from the cargo arrangement data
            containerId = item_data[0]["containerId"]
            print(f"Found item {itemId} in container {containerId}")
            
            # Convert itemId to integer for the URL
            url = f"http://localhost:8000/api/search?itemId={int(itemId)}"
            print(f"Making request to: {url}")
            response = await client.get(url)
            print(f"Response status code: {response.status_code}")
            print(f"Response body: {response.text}")
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Search endpoint returned status code: {response.status_code}")
                return {"success": False, "found": False, "retrieval_steps": []}
        except Exception as e:
            print(f"Error calling search endpoint: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return {"success": False, "found": False, "retrieval_steps": []}

def parse_position(position_str: str) -> dict:
    """
    Parse a position string formatted as:
    "(x,y,z),(x,y,z)"
    and return a dict with startCoordinates and endCoordinates.
    """
    pattern = r"\((.*?)\)"
    matches = re.findall(pattern, position_str)

    if len(matches) != 2:
        return {
            "startCoordinates": {"width": 0, "depth": 0, "height": 0},
            "endCoordinates": {"width": 0, "depth": 0, "height": 0}
        }

    try:
        def parse_tuple(tuple_str: str) -> dict:
            values = [float(v) for v in tuple_str.split(",")]
            return {"width": values[0], "depth": values[1], "height": values[2]}
        
        start_coords = parse_tuple(matches[0])
        end_coords = parse_tuple(matches[1])
        
        return {
            "startCoordinates": start_coords,
            "endCoordinates": end_coords
        }
    except Exception as e:
        print(f"Error parsing position tuple: {str(e)}")
        return {
            "startCoordinates": {"width": 0, "depth": 0, "height": 0},
            "endCoordinates": {"width": 0, "depth": 0, "height": 0}
        }

@router.get("/identify")
async def identify_waste():
    waste_file = "waste_items.csv"
    imported_file = "imported_items.csv"
    waste_items = []
    new_waste_items = []  # To track newly identified waste items for appending

    # Load existing waste items from waste_items.csv if it exists.
    if os.path.exists(waste_file):
        try:
            waste_df = pl.read_csv(waste_file)
            if not waste_df.is_empty():
                for item in waste_df.to_dicts():
                    position_value = item.get("position", "")
                    if isinstance(position_value, str):
                        if position_value.strip().startswith("{"):
                            try:
                                position_dict = json.loads(position_value)
                            except Exception as e:
                                print(f"JSON parsing error: {str(e)}")
                                position_dict = {
                                    "startCoordinates": {"width": 0, "depth": 0, "height": 0},
                                    "endCoordinates": {"width": 0, "depth": 0, "height": 0}
                                }
                        elif position_value.strip().startswith("("):
                            position_dict = parse_position(position_value)
                        else:
                            position_dict = {
                                "startCoordinates": {"width": 0, "depth": 0, "height": 0},
                                "endCoordinates": {"width": 0, "depth": 0, "height": 0}
                            }
                    else:
                        position_dict = {
                            "startCoordinates": {"width": 0, "depth": 0, "height": 0},
                            "endCoordinates": {"width": 0, "depth": 0, "height": 0}
                        }
                    
                    position_model = Position(
                        startCoordinates=position_dict.get("startCoordinates", {"width": 0, "depth": 0, "height": 0}),
                        endCoordinates=position_dict.get("endCoordinates", {"width": 0, "depth": 0, "height": 0})
                    )
                    
                    # Fix: Ensure itemId is cast to int safely with default value
                    try:
                        itemId = int(item.get("itemId", "0"))
                    except ValueError:
                        itemId = 0
                    
                    formatted_item = {
                        "itemId": itemId,
                        "name": str(item.get("name", "")),
                        "reason": str(item.get("reason", "")),
                        "containerId": str(item.get("containerId", "")),
                        "position": position_model.dict(),
                        "retrieval_steps": json.loads(item.get("retrieval_steps", "[]"))
                    }
                    waste_items.append(formatted_item)
        except Exception as e:
            print(f"Error reading waste_items.csv: {str(e)}")
    
    # Now, check imported_items.csv for expired items.
    if os.path.exists(imported_file):
        try:
            imported_df = pl.read_csv(imported_file)
            current_date = datetime.now().date()
            print(f"Current date: {current_date}")
            
            # Check for items with usageLimit = 0
            if "usageLimit" in imported_df.columns:
                zero_usageLimit_df = imported_df.filter(
                    (pl.col("usageLimit").is_not_null()) & 
                    (pl.col("usageLimit") == 0)
                )
                
                print(f"Found {len(zero_usageLimit_df)} items with usageLimit = 0")
                
                for item in zero_usageLimit_df.to_dicts():
                    print(f"Processing item with usageLimit = 0: {item}")
                    # Lookup containerId from cargo_arrangement.csv first
                    containerId = ""
                    position_str = "(0,0,0),(0,0,0)"  # Default value for CSV
                    retrieval_steps = []
                    # Initialize coordinates with default values
                    coordinates = {
                        "startCoordinates": {"width": 0, "depth": 0, "height": 0},
                        "endCoordinates": {"width": 0, "depth": 0, "height": 0}
                    }
                    
                    if os.path.exists("cargo_arrangement.csv"):
                        try:
                            cargo_df = pl.read_csv("cargo_arrangement.csv")
                            # Fix: Cast both sides to string for comparison
                            cargo_matching = cargo_df.filter(pl.col("itemId").cast(pl.Utf8) == str(item.get("itemId", ""))).to_dicts()
                            if cargo_matching:
                                containerId = str(cargo_matching[0].get("containerId", ""))
                                pos_str = cargo_matching[0].get("coordinates", "")
                                if pos_str:
                                    coordinates = parse_position(pos_str)
                                    position_str = pos_str
                                    
                                # Calculate retrieval steps
                                items_in_container = cargo_df.filter(
                                    (pl.col("containerId") == containerId) & 
                                    (pl.col("itemId").cast(str) != str(item.get("itemId", "")))
                                ).to_dicts()
                                
                                # Sort items by depth (front to back)
                                items_in_container.sort(key=lambda x: float(x["coordinates"].split(",")[1]))
                                
                                step_number = 1
                                
                                # Remove blocking items (front to back)
                                for blocking_item in items_in_container:
                                    retrieval_steps.append({
                                        "step": step_number,
                                        "action": "remove",
                                        "itemId": int(blocking_item["itemId"]),
                                        "item_name": blocking_item["name"]
                                    })
                                    step_number += 1
                                    
                                # Retrieve target item
                                retrieval_steps.append({
                                    "step": step_number,
                                    "action": "retrieve",
                                    "itemId": int(item.get("itemId", "0")),
                                    "item_name": item.get("name", "")
                                })
                                step_number += 1
                                
                                # Place back blocking items (back to front)
                                for blocking_item in reversed(items_in_container):
                                    retrieval_steps.append({
                                        "step": step_number,
                                        "action": "place",
                                        "itemId": int(blocking_item["itemId"]),
                                        "item_name": blocking_item["name"]
                                    })
                                    step_number += 1
                        except Exception as e:
                            print(f"Error reading cargo_arrangement.csv: {str(e)}")
                    
                    # Only if not found in cargo_arrangement.csv, try imported_containers.csv
                    if not containerId and os.path.exists("imported_containers.csv"):
                        try:
                            containers_df = pl.read_csv("imported_containers.csv")
                            # Assume imported_containers.csv has columns: containerId, zone, ...
                            matching_container = containers_df.filter(pl.col("zone") == item.get("preferredZone", "")).to_dicts()
                            if matching_container:
                                containerId = str(matching_container[0].get("containerId", ""))
                        except Exception as e:
                            print(f"Error reading imported_containers.csv: {str(e)}")
                    
                    # Fix: Ensure itemId is cast to int safely with default value
                    try:
                        itemId = int(item.get("itemId", "0"))
                    except ValueError:
                        itemId = 0
                    
                    # Create the formatted item for the API response
                    position_model = Position(
                        startCoordinates=coordinates.get("startCoordinates", {"width": 0, "depth": 0, "height": 0}),
                        endCoordinates=coordinates.get("endCoordinates", {"width": 0, "depth": 0, "height": 0})
                    )
                    
                    item_name = str(item.get("name", ""))
                    
                    zero_usage_item = {
                        "itemId": itemId,
                        "name": item_name,
                        "reason": "Usage Limit is 0",
                        "containerId": containerId,
                        "position": position_model.dict(),
                        "retrieval_steps": retrieval_steps
                    }
                    
                    # Create a simple dictionary for CSV export
                    csv_item = {
                        "itemId": itemId,
                        "name": item_name,
                        "reason": "Usage Limit is 0",
                        "containerId": containerId,
                        "position": position_str,
                        "retrieval_steps": json.dumps(retrieval_steps)
                    }
                    
                    # Only add to waste items if not already there
                    if not any(w["itemId"] == zero_usage_item["itemId"] for w in waste_items):
                        print(f"Adding item with usageLimit = 0 to waste items: {zero_usage_item}")
                        waste_items.append(zero_usage_item)
                        new_waste_items.append(csv_item)
            
            # Check for expired dates
            if "expiryDate" in imported_df.columns:
                # Try parsing dates in both formats using Polars
                # First try YYYY-MM-DD format
                try:
                    expired_df = imported_df.filter(
                        (pl.col("expiryDate").is_not_null()) & 
                        (pl.col("expiryDate").str.len_chars() > 0) &
                        (pl.col("expiryDate").str.strptime(pl.Date, format="%Y-%m-%d", strict=False) < current_date)
                    )
                except Exception as e:
                    print(f"Error parsing YYYY-MM-DD format: {str(e)}")
                    # If that fails, try DD-MM-YY format
                    try:
                        expired_df = imported_df.filter(
                            (pl.col("expiryDate").is_not_null()) & 
                            (pl.col("expiryDate").str.len_chars() > 0) &
                            (pl.col("expiryDate").str.strptime(pl.Date, format="%d-%m-%y", strict=False) < current_date)
                        )
                    except Exception as e:
                        print(f"Error parsing DD-MM-YY format: {str(e)}")
                        expired_df = pl.DataFrame()  # Empty DataFrame if both formats fail
                
                print(f"Found {len(expired_df)} items with expired dates")
                
                for item in expired_df.to_dicts():
                    print(f"Processing expired item: {item}")
                    # Lookup containerId from cargo_arrangement.csv first
                    containerId = ""
                    position_str = "(0,0,0),(0,0,0)"  # Default value for CSV
                    retrieval_steps = []
                    # Initialize coordinates with default values
                    coordinates = {
                        "startCoordinates": {"width": 0, "depth": 0, "height": 0},
                        "endCoordinates": {"width": 0, "depth": 0, "height": 0}
                    }
                    
                    if os.path.exists("cargo_arrangement.csv"):
                        try:
                            cargo_df = pl.read_csv("cargo_arrangement.csv")
                            # Fix: Cast both sides to string for comparison
                            cargo_matching = cargo_df.filter(pl.col("itemId").cast(pl.Utf8) == str(item.get("itemId", ""))).to_dicts()
                            if cargo_matching:
                                containerId = str(cargo_matching[0].get("containerId", ""))
                                pos_str = cargo_matching[0].get("coordinates", "")
                                if pos_str:
                                    coordinates = parse_position(pos_str)
                                    position_str = pos_str
                                    
                                # Calculate retrieval steps
                                items_in_container = cargo_df.filter(
                                    (pl.col("containerId") == containerId) & 
                                    (pl.col("itemId").cast(str) != str(item.get("itemId", "")))
                                ).to_dicts()
                                
                                # Sort items by depth (front to back)
                                items_in_container.sort(key=lambda x: float(x["coordinates"].split(",")[1]))
                                
                                step_number = 1
                                
                                # Remove blocking items (front to back)
                                for blocking_item in items_in_container:
                                    retrieval_steps.append({
                                        "step": step_number,
                                        "action": "remove",
                                        "itemId": int(blocking_item["itemId"]),
                                        "item_name": blocking_item["name"]
                                    })
                                    step_number += 1
                                    
                                # Retrieve target item
                                retrieval_steps.append({
                                    "step": step_number,
                                    "action": "retrieve",
                                    "itemId": int(item.get("itemId", "0")),
                                    "item_name": item.get("name", "")
                                })
                                step_number += 1
                                
                                # Place back blocking items (back to front)
                                for blocking_item in reversed(items_in_container):
                                    retrieval_steps.append({
                                        "step": step_number,
                                        "action": "place",
                                        "itemId": int(blocking_item["itemId"]),
                                        "item_name": blocking_item["name"]
                                    })
                                    step_number += 1
                        except Exception as e:
                            print(f"Error reading cargo_arrangement.csv: {str(e)}")
                    
                    # Only if not found in cargo_arrangement.csv, try imported_containers.csv
                    if not containerId and os.path.exists("imported_containers.csv"):
                        try:
                            containers_df = pl.read_csv("imported_containers.csv")
                            # Assume imported_containers.csv has columns: containerId, zone, ...
                            matching_container = containers_df.filter(pl.col("zone") == item.get("preferredZone", "")).to_dicts()
                            if matching_container:
                                containerId = str(matching_container[0].get("containerId", ""))
                        except Exception as e:
                            print(f"Error reading imported_containers.csv: {str(e)}")
                    
                    # Fix: Ensure itemId is cast to int safely with default value
                    try:
                        itemId = int(item.get("itemId", "0"))
                    except ValueError:
                        itemId = 0
                    
                    # Create the formatted item for the API response
                    position_model = Position(
                        startCoordinates=coordinates.get("startCoordinates", {"width": 0, "depth": 0, "height": 0}),
                        endCoordinates=coordinates.get("endCoordinates", {"width": 0, "depth": 0, "height": 0})
                    )
                    
                    item_name = str(item.get("name", ""))
                    
                    expired_item = {
                        "itemId": itemId,
                        "name": item_name,
                        "reason": "Expired",
                        "containerId": containerId,
                        "position": position_model.dict(),
                        "retrieval_steps": retrieval_steps
                    }
                    
                    # Create a simple dictionary for CSV export
                    csv_item = {
                        "itemId": itemId,
                        "name": item_name,
                        "reason": "Expired",
                        "containerId": containerId,
                        "position": position_str,
                        "retrieval_steps": json.dumps(retrieval_steps)
                    }
                    
                    # Only add to waste items if not already there
                    if not any(w["itemId"] == expired_item["itemId"] for w in waste_items):
                        print(f"Adding expired item to waste items: {expired_item}")
                        waste_items.append(expired_item)
                        new_waste_items.append(csv_item)
            
            # Now append the new waste items to waste_items.csv
            if new_waste_items:
                print(f"Appending {len(new_waste_items)} new waste items to waste_items.csv")
                
                # If the waste file exists, read it and combine with new items
                if os.path.exists(waste_file):
                    try:
                        # Read existing items
                        existing_items = []
                        with open(waste_file, 'r') as f:
                            reader = csv.DictReader(f)
                            existing_items = list(reader)
                            print(f"Found {len(existing_items)} existing items in waste_items.csv")
                        
                        # Add new items that aren't already in the file
                        existing_itemIds = {item['itemId'] for item in existing_items}
                        new_items_added = 0
                        for new_item in new_waste_items:
                            if str(new_item['itemId']) not in existing_itemIds:
                                existing_items.append(new_item)
                                new_items_added += 1
                        
                        print(f"Adding {new_items_added} new items to waste_items.csv")
                        
                        # Write all items back to the file
                        with open(waste_file, 'w', newline='') as f:
                            writer = csv.DictWriter(f, fieldnames=['itemId', 'name', 'reason', 'containerId', 'position', 'retrieval_steps'])
                            writer.writeheader()
                            writer.writerows(existing_items)
                        
                        print(f"Successfully wrote {len(existing_items)} items to waste_items.csv")
                    except Exception as e:
                        print(f"Error appending to waste_items.csv: {str(e)}")
                        print(f"Error type: {type(e)}")
                        import traceback
                        print(f"Traceback: {traceback.format_exc()}")
                else:
                    print("Creating new waste_items.csv")
                    # Create new file with waste items
                    try:
                        with open(waste_file, 'w', newline='') as f:
                            writer = csv.DictWriter(f, fieldnames=['itemId', 'name', 'reason', 'containerId', 'position', 'retrieval_steps'])
                            writer.writeheader()
                            writer.writerows(new_waste_items)
                        print(f"Successfully created waste_items.csv with {len(new_waste_items)} items")
                    except Exception as e:
                        print(f"Error creating waste_items.csv: {str(e)}")
                        print(f"Error type: {type(e)}")
                        import traceback
                        print(f"Traceback: {traceback.format_exc()}")
                    
        except Exception as e:
            print(f"Error processing imported_items.csv for expiry: {str(e)}")
    
    return {"success": True, "wasteItems": waste_items}

def calculate_volume(obj):
    width = abs(obj.end["width"] - obj.start["width"])
    depth = abs(obj.end["depth"] - obj.start["depth"])
    height = abs(obj.end["height"] - obj.start["height"])
    return width * depth * height

def read_waste_data(waste_filename, imported_filename):
    print(f"\nReading waste data from {waste_filename}")
    objects = []
    imported_items = load_imported_items(imported_filename)  # Use the function from waste_algo.py
    print(f"Loaded imported items: {imported_items}")
    weights = {}

    if not os.path.exists(waste_filename):
        print(f"Warning: {waste_filename} does not exist")
        return objects, weights
    
    try:
        waste_df = pl.read_csv(waste_filename)
        if waste_df.is_empty():
            print("Waste file is empty")
            return objects, weights
            
        for row in waste_df.to_dicts():
            print(f"\nProcessing row: {row}")
            
            # Get and validate itemId
            itemId = str(row.get("itemId", "")).strip()
            if not itemId:
                print(f"Skipping row with empty itemId: {row}")
                continue
            print(f"Processing itemId: {itemId}")
            
            # Get and validate containerId
            containerId = str(row.get("containerId", "")).strip()
            if not containerId:
                print(f"Skipping row with empty containerId: {row}")
                continue
            print(f"containerId: {containerId}")
            
            # Parse position
            position_str = str(row.get("position", ""))
            coordinates = parse_position(position_str)
            print(f"Parsed coordinates: {coordinates}")
            
            # Get weight from imported items
            weight = imported_items.get(itemId, 0)
            print(f"Found weight: {weight}")
            
            # Create Object3D with positional parameters
            obj = Object3D(
                itemId,
                str(row.get("name", "")),
                containerId,
                coordinates["startCoordinates"],
                coordinates["endCoordinates"]
            )
            print(f"Created Object3D: {obj.__dict__}")
            objects.append(obj)
            weights[itemId] = weight

    except Exception as e:
        print(f"Error reading waste data: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return objects, weights

    print(f"\nTotal objects read: {len(objects)}")
    print(f"Total weights: {weights}")
    return objects, weights

def calculate_retrieval_steps(itemId: int, containerId: str, cargo_df: pl.DataFrame, containers_df: pl.DataFrame) -> List[Dict]:
    """Calculate the steps needed to retrieve an item from a container."""
    print(f"\nCalculating retrieval steps for item {itemId} in container {containerId}")
    
    try:
        # Read imported items data for item details
        imported_df = pl.read_csv("imported_items.csv")
        print(f"Read imported items data with {len(imported_df)} rows")
        
        # Convert DataFrames to lists of dictionaries for ItemSearchSystem
        items_data = []
        for item in imported_df.to_dicts():
            items_data.append({
                "itemId": str(item.get("itemId", "")),
                "name": str(item.get("name", "")),
                "width": float(item.get("width", 0)),
                "depth": float(item.get("depth", 0)),
                "height": float(item.get("height", 0)),
                "priority": int(item.get("priority", 1)),
                "usageLimit": int(item.get("usageLimit", 0))
            })
            
        containers_data = containers_df.to_dicts()
        
        # Convert cargo data with proper position format
        cargo_data = []
        for item in cargo_df.to_dicts():
            position_str = item.get("coordinates", "")
            if position_str:
                try:
                    coords = [float(x) for x in position_str.replace('(', '').replace(')', '').split(',')]
                    if len(coords) >= 6:
                        cargo_data.append({
                            "itemId": str(item.get("itemId", "")),
                            "containerId": str(item.get("containerId", "")),
                            "zone": str(item.get("zone", "")),
                            "coordinates": position_str
                        })
                except Exception as e:
                    print(f"Error parsing coordinates for item {item.get('itemId', '')}: {str(e)}")
        
        # Create ItemSearchSystem instance
        search_system = ItemSearchSystem(
            items_data=items_data,
            containers_data=containers_data,
            cargo_data=cargo_data
        )
        
        # Search for the item using the optimized algorithm
        result = search_system.search_by_id(itemId)
        
        if not result.get("success", False) or not result.get("found", False):
            print(f"Item {itemId} not found or error in search: {result.get('message', '')}")
            return []
            
        # Convert the retrieval steps to the required format
        steps = []
        for step in result.get("retrieval_steps", []):
            steps.append({
                "action": step["action"],
                "itemId": str(step["itemId"]),
                "item_name": step.get("item_name", ""),
                "containerId": containerId,
                "zone": result.get("item", {}).get("zone", "")
            })
        
        print(f"Generated {len(steps)} retrieval steps")
        return steps
        
    except Exception as e:
        print(f"Error calculating retrieval steps: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return []

# Response models
class ReturnManifest(BaseModel):
    undocking_container_id: str
    undocking_date: str
    return_items: List[ReturnItem]
    total_volume: float
    total_weight: float

class ReturnPlanResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    return_plan: List[ReturnPlanStep] = Field(default_factory=list)
    retrieval_steps: List[RetrievalStep] = Field(default_factory=list)
    return_manifest: ReturnManifest

@router.post("/return-plan", response_model=ReturnPlanResponse)
async def generate_return_plan(request: ReturnPlanRequest):
    """Generate a return plan for waste items."""
    try:
        print("\nGenerating return plan...")
        print(f"Request: {request}")
        
        # Extract request data
        undocking_container_id = request.undocking_container_id
        undocking_date = request.undocking_date
        max_weight = float(request.max_weight) if request.max_weight else float('inf')
        
        # Load waste items and imported items data using the functions from waste_algo.py
        waste_items = load_waste_items()  # Using default filename
        imported_items = load_imported_items()  # Using default filename
        
        print(f"Loaded {len(waste_items)} waste items")
        print(f"Loaded {len(imported_items)} imported items")
        
        # Link waste items with their weights from imported items
        linked_items = link_waste_with_imported_items(waste_items, imported_items)
        print(f"Linked {len(linked_items)} items")
        
        # Filter items for the specified container
        container_items = [item for item in linked_items if item["containerId"] == undocking_container_id]
        print(f"Found {len(container_items)} items in container {undocking_container_id}")
        
        if not container_items:
            print(f"No items found in container {undocking_container_id}")
            return ReturnPlanResponse(
                success=True,
                return_plan=[],
                retrieval_steps=[],
                return_manifest=ReturnManifest(
                    undocking_container_id=undocking_container_id,
                    undocking_date=undocking_date,
                    return_items=[],
                    total_volume=0,
                    total_weight=0
                )
            )
        
        # Select optimal set of waste items using greedy approach
        selected_items, total_weight = select_waste_items_greedy(container_items, max_weight)
        print(f"Selected {len(selected_items)} items with total weight {total_weight} kg")
        
        # Generate return plan and retrieval steps using the renamed function
        return_plan, retrieval_steps = generate_return_plan_steps(selected_items, undocking_container_id)
        print(f"Generated {len(return_plan)} return plan steps")
        print(f"Generated {len(retrieval_steps)} retrieval steps")
        
        # Convert return plan steps to ReturnPlanStep objects
        return_plan_steps = []
        for step in return_plan:
            return_plan_steps.append(ReturnPlanStep(
                step=step["step"],
                itemId=str(step["itemId"]),
                item_name=step["itemName"],
                from_container=step["fromContainer"],
                to_container=step["toContainer"]
            ))
        
        # Convert retrieval steps to RetrievalStep objects
        retrieval_step_objects = []
        for step in retrieval_steps:
            retrieval_step_objects.append(RetrievalStep(
                step=step["step"],
                action=step["action"],
                itemId=int(step["itemId"]),
                item_name=step["itemName"]
            ))
        
        # Create return manifest
        return_manifest = create_return_manifest(
            selected_items, 
            undocking_container_id, 
            undocking_date, 
            total_weight
        )
        print(f"Created return manifest with {len(return_manifest['returnItems'])} items")
        
        # Convert return items to ReturnItem objects
        return_items = []
        for item in return_manifest["returnItems"]:
            return_items.append(ReturnItem(
                itemId=str(item["itemId"]),
                name=item["name"],
                reason=item["reason"]
            ))
        
        return ReturnPlanResponse(
            success=True,
            return_plan=return_plan_steps,
            retrieval_steps=retrieval_step_objects,
            return_manifest=ReturnManifest(
                undocking_container_id=undocking_container_id,
                undocking_date=undocking_date,
                return_items=return_items,
                total_volume=return_manifest["totalVolume"],
                total_weight=return_manifest["totalWeight"]
            )
        )
        
    except Exception as e:
        print(f"Error generating return plan: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return ReturnPlanResponse(
            success=False,
            error=str(e),
            return_plan=[],
            retrieval_steps=[],
            return_manifest=ReturnManifest(
                undocking_container_id=request.undocking_container_id if request else None,
                undocking_date=request.undocking_date if request else None,
                return_items=[],
                total_volume=0,
                total_weight=0
            )
        )

@router.post("/complete-undocking")
async def complete_undocking(request: CompleteUndockingRequest):
    waste_file = "waste_items.csv"
    items_file = "imported_items.csv"
    items_count = 0
    
    print(f"\nProcessing complete undocking for container {request.undocking_container_id}")
    
    # First, handle existing waste items
    if os.path.exists(waste_file):
        try:
            print(f"Reading waste items from {waste_file}")
            # Read all items from the CSV file
            with open(waste_file, 'r') as f:
                reader = csv.DictReader(f)
                all_items = list(reader)
                print(f"Found {len(all_items)} waste items")
            
            # Filter items to keep and count items to remove
            items_to_keep = []
            for item in all_items:
                if item['containerId'] == request.undocking_container_id:
                    items_count += 1
                    print(f"Removing item: {item}")
                else:
                    items_to_keep.append(item)
            
            print(f"Keeping {len(items_to_keep)} items, removing {items_count} items")
            
            # Write back the filtered items
            if items_to_keep:
                print(f"Writing {len(items_to_keep)} items back to {waste_file}")
                with open(waste_file, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=['itemId', 'name', 'reason', 'containerId', 'position', 'retrieval_steps'])
                    writer.writeheader()
                    writer.writerows(items_to_keep)
            else:
                print(f"No items remaining, deleting {waste_file}")
                os.remove(waste_file)
                
        except Exception as e:
            print(f"Error processing waste items: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
    else:
        print(f"Waste items file {waste_file} does not exist")
    
    # Then handle items that have reached their usage limit
    if os.path.exists(items_file):
        try:
            print(f"\nProcessing items from {items_file}")
            items_df = pl.read_csv(items_file)
            print(f"Found {len(items_df)} items")
            
            if "usage_count" in items_df.columns and "usageLimit" in items_df.columns:
                # Check for items that have reached their usage limit OR have a usage limit of 0
                expired_items = items_df.filter(
                    ((pl.col("usage_count") >= pl.col("usageLimit")) | 
                     (pl.col("usageLimit") == 0)) & 
                    (pl.col("containerId") == request.undocking_container_id)
                )
                
                if not expired_items.is_empty():
                    print(f"Found {len(expired_items)} expired items to remove")
                    # Remove items that have reached their usage limit OR have a usage limit of 0
                    items_df = items_df.filter(
                        ~(((pl.col("usage_count") >= pl.col("usageLimit")) | 
                           (pl.col("usageLimit") == 0)) & 
                          (pl.col("containerId") == request.undocking_container_id))
                    )
                    print(f"Writing {len(items_df)} remaining items back to {items_file}")
                    items_df.write_csv(items_file)
                else:
                    print("No expired items found to remove")
        except Exception as e:
            print(f"Error processing items at usage limit: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
    else:
        print(f"Items file {items_file} does not exist")
    
    print(f"\nComplete undocking finished. Removed {items_count} items.")
    return {"success": True, "items_removed": items_count}