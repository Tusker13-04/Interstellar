from fastapi import APIRouter, HTTPException, Request
from schemas import (
    CargoPlacementSystem, 
    PlacementRequest, 
    PlacementResponse,
    Item_for_search,
    Position,
    Coordinates,
    ItemForPlacement
)
from algos.placement_algo import AdvancedCargoPlacement
import polars as pl
from typing import List, Dict, Any, Union
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/api/placement",
    tags=["placement"],
)


class Container(BaseModel):
    containerId: str
    zone: str
    width: float
    depth: float
    height: float

class FrontendItem(BaseModel):
    itemId: str = Field(..., description="Item identifier")
    name: str = Field(..., description="Item name")
    width: float = Field(..., description="Item width in cm")
    depth: float = Field(..., description="Item depth in cm")
    height: float = Field(..., description="Item height in cm")
    mass: float = Field(..., description="Item mass in kg")
    priority: int = Field(..., description="Item priority")
    preferredZone: str = Field(..., description="Preferred zone for placement")

class FrontendPlacementInput(BaseModel):
    items: List[FrontendItem] = Field(..., description="List of items to place")
    containers: List[Container] = Field(..., description="List of available containers")

class PlacementInput(BaseModel):
    items: List[ItemForPlacement] = Field(..., description="List of items to place")
    containers: List[Container] = Field(..., description="List of available containers")

def transform_input(input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Transform input data to match the expected format for placement algorithm."""
    transformed_items = []
    for item in input_data["items"]:
        # Create Coordinates for start and end positions
        start_coords = {
            "width": 0,  # Initial position
            "depth": 0,
            "height": 0
        }
        end_coords = {
            "width": item["width"],
            "depth": item["depth"],
            "height": item["height"]
        }
        
        # Create Position
        position = {
            "startCoordinates": start_coords,
            "endCoordinates": end_coords
        }
        
        # Create transformed item
        transformed_item = {
            "itemId": str(item["itemId"]),
            "name": item["name"],
            "width": item["width"],
            "depth": item["depth"],
            "height": item["height"],
            "mass": item["mass"],
            "priority": item["priority"],
            "preferredZone": item["preferredZone"],
            "position": position
        }
        transformed_items.append(transformed_item)
    
    return transformed_items

def transform_frontend_input(input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Transform frontend input data to match the expected format for placement algorithm."""
    transformed_items = []
    for item in input_data["items"]:
        # Create Coordinates for start and end positions
        start_coords = {
            "width": 0,  # Initial position
            "depth": 0,
            "height": 0
        }
        end_coords = {
            "width": item["width"],
            "depth": item["depth"],
            "height": item["height"]
        }
        
        # Create Position
        position = {
            "startCoordinates": start_coords,
            "endCoordinates": end_coords
        }
        
        # Create transformed item
        transformed_item = {
            "itemId": str(item["itemId"]),  # Ensure itemId is string
            "name": item["name"],
            "width": item["width"],
            "depth": item["depth"],
            "height": item["height"],
            "mass": item["mass"],
            "priority": item["priority"],
            "preferredZone": item["preferredZone"],
            "position": position
        }
        transformed_items.append(transformed_item)
    
    return transformed_items

@router.post("/", response_model=PlacementResponse)
async def process_placement(input_data: Union[PlacementInput, FrontendPlacementInput]) -> PlacementResponse:
    try:
        # Check if input is in frontend format
        if "itemId" in input_data.items[0]:
            transformed_items = transform_frontend_input(input_data.dict())
        else:
            transformed_items = transform_input(input_data.dict())

        placements = []
        all_rearrangements = []

        # Process each container separately
        for container in input_data.containers:
            print(f"Processing container {container.containerId} for zone {container.zone}")
            
            # Initialize advanced placement algorithm for this container
            cargo_placer = AdvancedCargoPlacement({
                "width": container.width,
                "depth": container.depth,
                "height": container.height
            })

            # Get items assigned to this container's zone
            container_items = [
                item for item in transformed_items 
                if item["preferredZone"] == container.zone
            ]
            
            print(f"Found {len(container_items)} items for zone {container.zone}")

            if not container_items:
                continue

            # Find optimal placement for items in this container
            container_placements, container_rearrangements = cargo_placer.find_optimal_placement(container_items)
            print(f"Generated {len(container_placements)} placements and {len(container_rearrangements)} rearrangements for container {container.containerId}")

            # Add container ID to placements and rearrangements
            for placement in container_placements:
                placement["containerId"] = container.containerId
                placements.append(placement)
                
            for rearrangement in container_rearrangements:
                rearrangement["containerId"] = container.containerId
                all_rearrangements.append(rearrangement)

        success = len(placements) > 0
        print(f"Placement complete. Success: {success}, Total placements: {len(placements)}, Total rearrangements: {len(all_rearrangements)}")

        return PlacementResponse(
            success=success,
            placements=placements,
            rearrangements=all_rearrangements
        )

    except Exception as e:
        print(f"Error in placement processing: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))