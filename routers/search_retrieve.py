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

def find_suitable_position(container_id, item_width, item_depth, item_height, cargo_df, containers_df):
    """Find a suitable position for an item in a container."""
    # Get container dimensions and zone
    container_data = containers_df.filter(pl.col("containerId") == container_id)
    if container_data.is_empty():
        return None
    
    container_info = container_data.row(0, named=True)
    container_width = float(container_info["width"])
    container_depth = float(container_info["depth"])
    container_height = float(container_info["height"])
    container_zone = container_info["zone"]
    
    # Check if item fits in current container
    if (item_width > container_width or 
        item_depth > container_depth or 
        item_height > container_height):
        # Item is too big for this container, find a bigger container in the same zone
        bigger_containers = containers_df.filter(
            (pl.col("zone") == container_zone) &
            (pl.col("width") >= item_width) &
            (pl.col("depth") >= item_depth) &
            (pl.col("height") >= item_height)
        )
        
        if not bigger_containers.is_empty():
            # Found bigger containers, suggest moving to the smallest one that fits
            bigger_containers = bigger_containers.sort(
                by=["width", "depth", "height"]
            )
            suggested_container = bigger_containers.row(0, named=True)
            print(f"Item too big for {container_id}, suggesting move to {suggested_container['containerId']}")
            return None
            
        print(f"No suitable container found in zone {container_zone} for item dimensions {item_width}x{item_depth}x{item_height}")
        return None
    
    # Get existing items in the container
    existing_items = cargo_df.filter(pl.col("containerId") == container_id)
    
    # If no existing items, place at origin
    if existing_items.is_empty():
        return {
            "startCoordinates": {"width": 0, "depth": 0, "height": 0},
            "endCoordinates": {"width": item_width, "depth": item_depth, "height": item_height}
        }
    
    # Check if any existing items should be moved to smaller containers
    for item in existing_items.iter_rows(named=True):
        coords = item["coordinates"].strip()[1:-1].split("),(")
        item_start = [float(x) for x in coords[0].split(",")]
        item_end = [float(x) for x in coords[1].split(",")]
        
        existing_width = item_end[0] - item_start[0]
        existing_depth = item_end[1] - item_start[1]
        existing_height = item_end[2] - item_start[2]
        
        # Find smaller containers that could fit this item
        smaller_containers = containers_df.filter(
            (pl.col("zone") == container_zone) &
            (pl.col("width") >= existing_width) &
            (pl.col("depth") >= existing_depth) &
            (pl.col("height") >= existing_height) &
            (pl.col("width") < container_width) &
            (pl.col("depth") < container_depth) &
            (pl.col("height") < container_height)
        )
        
        if not smaller_containers.is_empty():
            print(f"Item {item['itemId']} could be moved to a smaller container in zone {container_zone}")
    
    # Try to find a position in the current container
    # Try positions along the width axis
    for x in range(0, int(container_width - item_width) + 1, 5):
        # Try positions along the depth axis
        for y in range(0, int(container_depth - item_depth) + 1, 5):
            # Try positions along the height axis
            for z in range(0, int(container_height - item_height) + 1, 5):
                # Check if this position overlaps with any existing items
                position_valid = True
                
                for item in existing_items.iter_rows(named=True):
                    item_coordinates = item["coordinates"]
                    coordinates = item_coordinates.strip()[1:-1].split("),(")
                    item_start = coordinates[0].split(",")
                    item_start = (float(item_start[0]), float(item_start[1]), float(item_start[2]))
                    item_end = coordinates[1].split(",")
                    item_end = (float(item_end[0]), float(item_end[1]), float(item_end[2]))
                    
                    # Check for overlap
                    if (x < item_end[0] and (x + item_width) > item_start[0] and
                        y < item_end[1] and (y + item_depth) > item_start[1] and
                        z < item_end[2] and (z + item_height) > item_start[2]):
                        position_valid = False
                        break
                
                if position_valid:
                    return {
                        "startCoordinates": {"width": x, "depth": y, "height": z},
                        "endCoordinates": {"width": x + item_width, "depth": y + item_depth, "height": z + item_height}
                    }
    
    return None

@router.post("/place", response_model=PlaceItemResponse)
async def place_item(request: PlaceItemRequest):
    try:
        if not request.timestamp:
            request.timestamp = datetime.datetime.now().isoformat()

        # Use the file paths defined at the top of the file
        cargo_file = "temp_cargo_arrangement.csv"
        temp_cargo_file = "temp_cargo_arrangement.csv"
        containers_file = "temp_imported_containers.csv"
        items_file = "temp_imported_items.csv"

        if not os.path.exists(cargo_file) or not os.path.exists(containers_file) or not os.path.exists(items_file):
            print(f"Required files not found")
            return {"success": False}

        cargo_df = pl.read_csv(cargo_file)
        containers_df = pl.read_csv(containers_file)
        items_df = pl.read_csv(items_file)

        print(f"Cargo columns: {cargo_df.columns}")
        print(f"Containers columns: {containers_df.columns}")

        # Convert itemId to integer for comparison
        item_id = int(request.itemId) if isinstance(request.itemId, str) else request.itemId

        # Get item dimensions
        item_data = items_df.filter(pl.col("itemId") == item_id)
        if item_data.is_empty():
            print(f"Item ID {item_id} not found")
            return {"success": False}
        
        item_info = item_data.row(0, named=True)
        item_width = float(item_info["width"])
        item_depth = float(item_info["depth"])
        item_height = float(item_info["height"])

        container_data = containers_df.filter(pl.col("containerId") == request.containerId)
        if container_data.is_empty():
            print(f"Container ID {request.containerId} not found")
            return {"success": False}

        container_info = container_data.row(0, named=True)
        zone = container_info["zone"]

        # Get all containers in the same zone
        zone_containers = containers_df.filter(pl.col("zone") == zone)
        
        # Sort containers by size (volume)
        zone_containers = zone_containers.with_columns([
            (pl.col("width") * pl.col("depth") * pl.col("height")).alias("volume")
        ]).sort("volume")

        # Find the smallest container that can fit the item
        suitable_container = None
        for container in zone_containers.iter_rows(named=True):
            if (item_width <= float(container["width"]) and
                item_depth <= float(container["depth"]) and
                item_height <= float(container["height"])):
                suitable_container = container
                break

        if suitable_container and suitable_container["containerId"] != request.containerId:
            # A more suitable container was found
            print(f"Suggesting container {suitable_container['containerId']} for item {item_id}")
            request.containerId = suitable_container["containerId"]

        # If position is not provided, find a suitable position
        if not request.position:
            position = find_suitable_position(request.containerId, item_width, item_depth, item_height, cargo_df, containers_df)
            if not position:
                print(f"No suitable position found for item {item_id} in container {request.containerId}")
                return {"success": False}
            request.position = position

        # Get coordinates from the request's Position object
        start_coords = request.position.startCoordinates
        end_coords = request.position.endCoordinates
        
        # Create coordinate string in the expected format
        coordinates_str = f"({start_coords.width},{start_coords.depth},{start_coords.height}),({end_coords.width},{end_coords.depth},{end_coords.height})"

        # Check for existing items that could be moved to smaller containers
        existing_items = cargo_df.filter(pl.col("containerId") == request.containerId)
        for item in existing_items.iter_rows(named=True):
            coords = item["coordinates"].strip()[1:-1].split("),(")
            item_start = [float(x) for x in coords[0].split(",")]
            item_end = [float(x) for x in coords[1].split(",")]
            
            existing_width = item_end[0] - item_start[0]
            existing_depth = item_end[1] - item_start[1]
            existing_height = item_end[2] - item_start[2]
            
            # Find smaller containers that could fit this item
            smaller_containers = zone_containers.filter(
                (pl.col("width") >= existing_width) &
                (pl.col("depth") >= existing_depth) &
                (pl.col("height") >= existing_height) &
                (pl.col("volume") < float(container_info["width"]) * float(container_info["depth"]) * float(container_info["height"]))
            )
            
            if not smaller_containers.is_empty():
                smaller_container = smaller_containers.row(0, named=True)
                # Try to move the item to the smaller container
                new_position = find_suitable_position(
                    smaller_container["containerId"],
                    existing_width,
                    existing_depth,
                    existing_height,
                    cargo_df,
                    containers_df
                )
                
                if new_position:
                    # Update the item's position in the smaller container
                    cargo_df = cargo_df.with_columns([
                        pl.when(pl.col("itemId") == int(item["itemId"]))
                        .then(pl.lit(smaller_container["containerId"]))
                        .otherwise(pl.col("containerId"))
                        .alias("containerId"),
                        
                        pl.when(pl.col("itemId") == int(item["itemId"]))
                        .then(pl.lit(f"({new_position['startCoordinates']['width']},{new_position['startCoordinates']['depth']},{new_position['startCoordinates']['height']}),({new_position['endCoordinates']['width']},{new_position['endCoordinates']['depth']},{new_position['endCoordinates']['height']})"))
                        .otherwise(pl.col("coordinates"))
                        .alias("coordinates")
                    ])
                else:
                    print(f"Could not find suitable position in smaller container for item {item['itemId']}")
            else:
                print(f"No smaller containers available for item {item['itemId']}")

        # Check for overlaps in the target container
        overlapping_items = cargo_df.filter(
            (pl.col("containerId") == request.containerId) & 
            (pl.col("itemId") != item_id)
        )

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

            # Check if the new item's position overlaps with existing items
            if (start[0] < item_end[0] and end[0] > item_start[0] and 
                start[1] < item_end[1] and end[1] > item_start[1] and 
                start[2] < item_end[2] and end[2] > item_start[2]):
                overlapping = True
                break

        if overlapping:
            print(f"Cannot place item {request.itemId} in container {request.containerId} due to overlap")
            return {"success": False}

        # Update the cargo files
        item_exists = not cargo_df.filter(pl.col("itemId") == item_id).is_empty()
        if item_exists:
            cargo_df = cargo_df.with_columns([
                pl.when(pl.col("itemId") == item_id)
                .then(pl.lit(zone))
                .otherwise(pl.col("zone"))
                .alias("zone"),
                pl.when(pl.col("itemId") == item_id)
                .then(pl.lit(coordinates_str))
                .otherwise(pl.col("coordinates"))
                .alias("coordinates"),
                pl.when(pl.col("itemId") == item_id)
                .then(pl.lit(request.containerId))
                .otherwise(pl.col("containerId"))
                .alias("containerId")
            ])
        else:
            new_row = pl.DataFrame({
                "itemId": [item_id],
                "zone": [zone],
                "containerId": [request.containerId],
                "coordinates": [coordinates_str]
            })
            cargo_df = pl.concat([cargo_df, new_row])

        # Save the updated cargo files
        cargo_df.write_csv(cargo_file)
        cargo_df.write_csv(temp_cargo_file)

        return {"success": True}

    except Exception as e:
        print(f"Error in place endpoint: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {"success": False}