from fastapi import APIRouter, HTTPException, Query, Depends
import polars as pl
import os
import re
from typing import Optional, List
from schemas import (
    Coordinates, 
    Position, 
    Item_for_search, 
    SearchResponse, 
    RetrievalStep,
    RetrieveItemRequest,  
    PlaceItemRequest,           
    PlaceItemResponse,
    CargoPlacementSystem,
    RetrieveResponse
)
import datetime
import csv
from algos.retrieve_algo import PriorityAStarRetrieval, RetrievalPath
from algos.search_algo import ItemSearchSystem
import numpy as np
import pandas as pd
import io
import json
from datetime import datetime, timezone

router = APIRouter(
    prefix="/api",
    tags=["search_retrieve"],
)

cargo_file = "temp_cargo_arrangement.csv"
items_file = "temp_imported_items.csv"
containers_file = "temp_imported_containers.csv"

cargo_system = CargoPlacementSystem()

LOG_FILE = "logs.csv"

# DataFrame to store logs
log_columns = ["timestamp", "userId", "action_type", "itemId", "details"]
logs_df = pl.DataFrame(schema={
    "timestamp": pl.Utf8,
    "userId": pl.Utf8,
    "action_type": pl.Utf8,
    "itemId": pl.Int64,
    "details": pl.Utf8
})

def convert_timestamp(timestamp):
    """Convert timestamps in Z format to +00:00 format."""
    if timestamp and timestamp.endswith('Z'):
        return timestamp.replace('Z', '+00:00')
    return timestamp

def log_action(action_type: str, details: dict = None, userId: str = "", itemId: int = 0, timestamp: str = None):
    global logs_df

    if not isinstance(details, dict):  # Ensure details is a dictionary
        details = {"message": str(details)}

    # Convert details to JSON string
    details_json = json.dumps(details)

    # Use provided timestamp or generate current timestamp
    if timestamp:
        # Convert from Z format to +00:00 format if needed
        timestamp = convert_timestamp(timestamp)
    else:
        timestamp = datetime.now(timezone.utc).isoformat()

    # Create new log entry with proper types
    new_entry = pl.DataFrame({
        "timestamp": [timestamp],
        "userId": [str(userId)],
        "action_type": [str(action_type)],
        "itemId": [int(itemId) if itemId is not None else 0],
        "details": [details_json]
    })

    # Load existing logs if file exists
    if os.path.exists(LOG_FILE):
        existing_logs = pl.read_csv(LOG_FILE)
        # Rename userId to userId if it exists
        if "userId" in existing_logs.columns:
            existing_logs = existing_logs.rename({"userId": "userId"})
        logs_df = pl.concat([existing_logs, new_entry], how="vertical")
    else:
        logs_df = new_entry

    # Save to CSV
    logs_df.write_csv(LOG_FILE)

@router.get("/search", response_model=SearchResponse)
async def search_item(
    itemId: Optional[int] = Query(None),
    name: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None, description="Optional user ID for logging purposes")
):
    try:
        # Load and validate required files
        if not all(os.path.exists(file) for file in [items_file, containers_file, cargo_file]):
            print(f"Missing required files. Checking: {items_file}, {containers_file}, {cargo_file}")
            return SearchResponse(success=False, found=False)

        # Load all required data
        items_df = pl.read_csv(items_file)
        containers_df = pl.read_csv(containers_file)
        cargo_df = pl.read_csv(cargo_file)

        if items_df.is_empty() or containers_df.is_empty() or cargo_df.is_empty():
            print("One or more data files are empty")
            return SearchResponse(success=False, found=False)

        # Convert DataFrames to list of dicts
        items_data = items_df.to_dicts()
        containers_data = containers_df.to_dicts()
        cargo_data = cargo_df.to_dicts()
        
        # Initialize search system
        search_system = ItemSearchSystem(
            items_data=items_data,
            containers_data=containers_data,
            cargo_data=cargo_data
        )
        
        # Perform search based on input
        if itemId is not None:
            print(f"Searching for itemId: {itemId}")
            result = search_system.search_by_id(itemId)
        elif name is not None:
            print(f"Searching for name: {name}")
            result = search_system.search_by_name(name)
        else:
            raise HTTPException(status_code=400, detail="Either itemId or name must be provided")

        # Handle search results
        if not result["success"]:
            print(f"Search unsuccessful: {result.get('message', 'Unknown error')}")
            return SearchResponse(success=False, found=False)
            
        if not result["found"]:
            print(f"Item not found: {result.get('message', 'Unknown reason')}")
            return SearchResponse(success=True, found=False)
            
        # Convert successful result to SearchResponse format
        try:
            print(f"Item found: {result['item']}")
            
            # Create the response
            response = SearchResponse(
                success=True,
                found=True,
                item=Item_for_search(
                    itemId=result["item"]["itemId"],
                    name=result["item"]["name"],
                    containerId=result["item"]["containerId"],
                    zone=result["item"]["zone"],
                    position=Position(
                        startCoordinates=Coordinates(**result["item"]["position"]["startCoordinates"]),
                        endCoordinates=Coordinates(**result["item"]["position"]["endCoordinates"])
                    )
                ),
                retrieval_steps=[
                    RetrievalStep(
                        step=step["step"],
                        action=step["action"],
                        itemId=step["itemId"],
                        item_name=step["item_name"]
                    ) for step in (result.get("retrieval_steps") or [])
                ]
            )
            
            # Log the search if user_id is provided
            if user_id:
                from routers.logs import log_action
                # Use current timestamp
                log_action(
                    user_id=user_id,
                    action_type="search",
                    itemId=result["item"]["itemId"],
                    details={"search_type": "id" if itemId else "name", "query": itemId or name}
                )
                
            return response
            
        except Exception as e:
            print(f"Error formatting response: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return SearchResponse(success=False, found=False)
            
    except Exception as e:
        print(f"Error in search endpoint: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return SearchResponse(success=False, found=False)

@router.post("/retrieve")
async def retrieve_item(request: RetrieveItemRequest):
    try:
        itemId = request.itemId
        userId = request.userId
        timestamp = request.timestamp

        if not timestamp:
            timestamp = datetime.datetime.now().isoformat()

        items_file = "temp_imported_items.csv"    
        containers_file = "temp_imported_containers.csv"
        cargo_file = "temp_cargo_arrangement.csv"
        temp_cargo_file = "temp_cargo_arrangement.csv"
        waste_file = "waste_items.csv"

        # Check if required files exist
        if not os.path.exists(items_file) or not os.path.exists(containers_file):
            print(f"Missing required files. Please ensure all files exist.")
            return {"success": False}

        # For retrieval, we'll prefer the temp cargo file if it exists, as it maintains original usage limits
        cargo_read_file = temp_cargo_file if os.path.exists(temp_cargo_file) else cargo_file

        # Load CSV data
        items_df = pl.read_csv(items_file)
        cargo_df = pl.read_csv(cargo_read_file)
        containers_df = pl.read_csv(containers_file)
        
        print(f"Reading cargo data from: {cargo_read_file}")

        # Check if item exists in cargo
        item_in_cargo = cargo_df.filter(pl.col("itemId") == itemId)
        if item_in_cargo.is_empty():
            return {"success": False}

        # Check if item exists in items database
        item_data = items_df.filter(pl.col("itemId") == itemId)
        if item_data.is_empty():
            print(f"Item {itemId} not found in items database")
            return {"success": False}

        # Get zone and container information
        zone = item_in_cargo.select("zone")[0, 0]
        container_data = containers_df.filter(pl.col("zone") == zone)
        if container_data.is_empty():
            print(f"No container found for zone {zone}")
            return {"success": False}

        # Initialize retrieval algorithm with container dimensions
        container_dims = container_data.row(0, named=True)
        retriever = PriorityAStarRetrieval({
            "width": float(container_dims["width"]),
            "depth": float(container_dims["depth"]),
            "height": float(container_dims["height"])
        })

        # Parse item coordinates
        coord_str = item_in_cargo.select("coordinates")[0, 0]
        print(f"Item coordinates: {coord_str}")
        coords = re.findall(r'[-+]?\d*\.\d+|[-+]?\d+', coord_str)
        
        if len(coords) < 6:
            print(f"Invalid coordinates format: {coord_str}")
            return {"success": False}

        # Check usage limit and update
        current_usage = int(items_df.filter(pl.col("itemId") == itemId).select("usageLimit")[0, 0])
        if current_usage <= 0:
            return {"success": False}

        # Update usage limit in the items file
        new_usage = current_usage - 1
        print(f"New usage limit for item {itemId}: {new_usage}")

        updated_items_df = items_df.with_columns(
            pl.when(pl.col("itemId") == itemId)
            .then(pl.lit(new_usage))
            .otherwise(pl.col("usageLimit"))
            .alias("usageLimit")
        )

        # Write updated items data
        updated_items_df.write_csv(items_file)
        log_retrieval(itemId, userId, timestamp)

        # Handle items with no uses left - only update the main cargo file
        if new_usage == 0:
            print(f"Removing item {itemId} from main cargo file as it has 0 uses left")
            # Load the main cargo file for updating
            main_cargo_df = pl.read_csv(cargo_file)
            updated_cargo_df = main_cargo_df.filter(pl.col("itemId") != itemId)
            updated_cargo_df.write_csv(cargo_file)

            containerId = container_data.select("containerId")[0, 0]
            position_data = item_in_cargo.select("coordinates")[0, 0]

            add_to_waste_items(
                itemId=itemId,
                name=item_data.select("name")[0, 0],
                reason="Out of Uses",
                containerId=containerId,
                position=position_data
            )

        return {"success": True}

    except Exception as e:
        print(f"Error in retrieve endpoint: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {"success": False}

def add_to_waste_items(itemId, name, reason, containerId, position):
    waste_file = "waste_items.csv"
    new_waste_item = pl.DataFrame({
        "itemId": [int(itemId)],
        "name": [name],
        "reason": [reason],
        "containerId": [str(containerId)],
        "position": [str(position)]
    })

    if not os.path.exists(waste_file):
        print(f"Creating new waste_items.csv file with item {itemId}")
        new_waste_item.write_csv(waste_file)
    else:
        try:
            waste_df = pl.read_csv(waste_file)
            print(f"Appending item {itemId} to existing waste_items.csv")
            updated_waste_df = pl.concat([waste_df, new_waste_item])
            updated_waste_df.write_csv(waste_file)
        except Exception as e:
            print(f"Error appending to waste_items.csv: {str(e)}")
            print(f"Creating new waste_items.csv file with item {itemId}")
            new_waste_item.write_csv(waste_file)

    print(f"Added item {itemId} to waste items with reason: {reason}")

def log_retrieval(itemId, userId, timestamp):
    log_file = "item_retrievals.csv"
    
    # Convert timestamp if needed
    timestamp = convert_timestamp(timestamp)
    
    if not os.path.exists(log_file):
        with open(log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['itemId', 'userId', 'timestamp'])
    
    with open(log_file, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([itemId, userId, timestamp])

@router.post("/place", response_model=PlaceItemResponse)
async def place_item(request: PlaceItemRequest):
    try:
        if not request.timestamp:
            request.timestamp = datetime.datetime.now().isoformat()

        cargo_file = "cargo_arrangement.csv"
        temp_cargo_file = "temp_cargo_arrangement.csv"
        containers_file = "imported_containers.csv"

        if not os.path.exists(cargo_file) or not os.path.exists(containers_file):
            print(f"Required files not found")
            return {"success": False}

        cargo_df = pl.read_csv(cargo_file)
        containers_df = pl.read_csv(containers_file)

        print(f"Cargo columns: {cargo_df.columns}")
        print(f"Containers columns: {containers_df.columns}")

        container_data = containers_df.filter(pl.col("containerId") == request.containerId)
        if container_data.is_empty():
            print(f"Container ID {request.containerId} not found")
            return {"success": False}

        container_info = container_data.row(0, named=True)
        zone = container_info["zone"]

        # Get coordinates from the request's Position object
        start_coords = request.position.startCoordinates
        end_coords = request.position.endCoordinates
        
        # Create coordinate string in the expected format
        coordinates_str = f"({start_coords.width},{start_coords.depth},{start_coords.height}),({end_coords.width},{end_coords.depth},{end_coords.height})"

        item_exists = not cargo_df.filter(pl.col("itemId") == request.itemId).is_empty()

        overlapping_items = cargo_df.filter(
            (pl.col("zone") == zone) & 
            (pl.col("itemId") != request.itemId)
        )

        print(f"Checking for overlaps in container {request.containerId} at zone {zone}")
        print(f"New item position: start={start_coords}, end={end_coords}")

        overlapping = False
        for item in overlapping_items.iter_rows(named=True):
            item_coordinates = item["coordinates"]
            coordinates = item_coordinates.strip()[1:-1].split("),(")
            item_start = coordinates[0].split(",")
            item_start = (float(item_start[0]), float(item_start[1]), float(item_start[2]))
            item_end = coordinates[1].split(",")
            item_end = (float(item_end[0]), float(item_end[1]), float(item_end[2]))

            # Create tuples for comparison
            start = (start_coords.width, start_coords.depth, start_coords.height)
            end = (end_coords.width, end_coords.depth, end_coords.height)

            print(f"Checking against item {item['itemId']} at coordinates {item_coordinates}")
            print(f"Item start: {item_start}, Item end: {item_end}")
            print(f"New item start: {start}, New item end: {end}")

            # Check if the new item's position overlaps with existing items
            # Using inclusive inequalities to handle adjacent items correctly
            if (start[0] <= item_end[0] and end[0] >= item_start[0] and 
                start[1] <= item_end[1] and end[1] >= item_start[1] and 
                start[2] <= item_end[2] and end[2] >= item_start[2]):
                print(f"Overlap detected with item {item['itemId']} at coordinates {item_coordinates}")
                overlapping = True
                break

        if overlapping:
            print(f"Cannot place item {request.itemId} in container {request.containerId} due to overlap")
            return {"success": False}

        # Update the main cargo arrangement file
        if item_exists:
            # For the main cargo file
            updated_cargo_df = cargo_df.with_columns([
                pl.when(pl.col("itemId") == request.itemId)
                  .then(pl.lit(zone))
                  .otherwise(pl.col("zone"))
                  .alias("zone"),
                pl.when(pl.col("itemId") == request.itemId)
                  .then(pl.lit(coordinates_str))
                  .otherwise(pl.col("coordinates"))
                  .alias("coordinates")
            ])
            updated_cargo_df.write_csv(cargo_file)
        else:
            new_row = pl.DataFrame({
                "itemId": [request.itemId],
                "zone": [zone],
                "coordinates": [coordinates_str]
            })
            updated_cargo_df = pl.concat([cargo_df, new_row])
            updated_cargo_df.write_csv(cargo_file)
        
        # Also update the temp cargo arrangement file if it exists
        if os.path.exists(temp_cargo_file):
            try:
                temp_cargo_df = pl.read_csv(temp_cargo_file)
                temp_item_exists = not temp_cargo_df.filter(pl.col("itemId") == request.itemId).is_empty()
                
                if temp_item_exists:
                    # Update existing item in temp file
                    updated_temp_df = temp_cargo_df.with_columns([
                        pl.when(pl.col("itemId") == request.itemId)
                          .then(pl.lit(zone))
                          .otherwise(pl.col("zone"))
                          .alias("zone"),
                        pl.when(pl.col("itemId") == request.itemId)
                          .then(pl.lit(coordinates_str))
                          .otherwise(pl.col("coordinates"))
                          .alias("coordinates")
                    ])
                    updated_temp_df.write_csv(temp_cargo_file)
                else:
                    # Add new item to temp file
                    new_row = pl.DataFrame({
                        "itemId": [request.itemId],
                        "zone": [zone],
                        "coordinates": [coordinates_str]
                    })
                    updated_temp_df = pl.concat([temp_cargo_df, new_row])
                    updated_temp_df.write_csv(temp_cargo_file)
                
                print(f"Updated both {cargo_file} and {temp_cargo_file}")
            except Exception as e:
                print(f"Error updating temp cargo file: {str(e)}")
                print(f"Only updated the main cargo file")
        else:
            # Just copy the main file to the temp file
            updated_cargo_df.write_csv(temp_cargo_file)
            print(f"Created new {temp_cargo_file} as a copy of {cargo_file}")

        return {"success": True}

    except Exception as e:
        print(f"Error in place endpoint: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {"success": False}