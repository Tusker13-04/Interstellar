import csv
import io
import polars as pl
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File, Response
from schemas import CargoPlacementSystem, ImportItemsResponse, ImportContainersResponse, CargoArrangementExport, Coordinates
import polars as pl
import json
import os

router = APIRouter(
    prefix="/api",
    tags=["import-export"]
)

cargo_system = CargoPlacementSystem()

LOG_FILE = "logs.csv"

# DataFrame to store logs
log_columns = ["timestamp", "userId", "action_type", "itemId", "details"]
logs_df = pl.DataFrame(schema={
    "timestamp": pl.Utf8,
    "userId": pl.Utf8,
    "action_type": pl.Utf8,
    "itemId": pl.Int64, # TO integer
    "details": pl.Utf8  # Store details as a string (JSON)
})

def convert_timestamp(timestamp):
    """Convert timestamps in Z format to +00:00 format."""
    if timestamp and timestamp.endswith('Z'):
        return timestamp.replace('Z', '+00:00')
    return timestamp

def log_action(action_type: str, details: dict = None, userId: str = "", itemId: int = 0, timestamp: str = None):
    global logs_df

    if not isinstance(details, dict):  # Ensure details is a dictionary
        details = {"from_container": "", "to_container": "", "reason": str(details)}

    structured_details = {
        "from_container": details.get("from_container", ""),
        "to_container": details.get("to_container", ""),
        "reason": details.get("reason", "")
    }

    details_json = json.dumps(structured_details)  # Store as JSON string

    # Use provided timestamp or generate current timestamp
    if timestamp:
        # Convert from Z format to +00:00 format if needed
        timestamp = convert_timestamp(timestamp)
    else:
        timestamp = datetime.now(timezone.utc).isoformat()

    new_entry = pl.DataFrame(
        {
            "timestamp": [timestamp],
            "userId": [userId],
            "action_type": [action_type],
            "itemId": [itemId],
            "details": [details_json],  # Ensure JSON format
        }
    )

    logs_df = pl.concat([logs_df, new_entry], how="vertical")
    logs_df.write_csv(LOG_FILE)

def convert_csv_to_json(file_contents: str):
    """ Convert CSV data to a list of dictionaries (JSON format). """
    reader = csv.DictReader(io.StringIO(file_contents))
    return [row for row in reader]

### **1. Import Items from CSV**
@router.post("/import/items", response_model=ImportItemsResponse)
async def import_items(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    try:
        contents = await file.read()
        decoded_contents = contents.decode("utf-8").strip()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    if not decoded_contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Validate required columns
    reader = csv.DictReader(io.StringIO(decoded_contents))
    required_columns = {
        "itemId", "name", "width", "depth", "height", 
        "mass", "priority", "expiryDate", "usageLimit", "preferredZone"
    }

    if not required_columns.issubset(set(reader.fieldnames or [])):
        missing_columns = required_columns - set(reader.fieldnames or [])
        raise HTTPException(status_code=400, detail=f"Missing required columns: {missing_columns}")

    # Convert CSV to JSON
    items_json = convert_csv_to_json(decoded_contents)

    items = []
    errors = []

    for row_number, row in enumerate(items_json, start=1):
        try:
            # Convert and validate required fields
            itemId = int(row["itemId"])
            width = float(row["width"])
            depth = float(row["depth"])
            height = float(row["height"])
            mass = float(row["mass"])
            priority_value = int(row["priority"])
            preferredZone = row["preferredZone"]
            name = row["name"]

            if not (1 <= priority_value <= 100):
                raise ValueError("Priority must be between 1 and 100.")

            # Handle expiry date conversion safely
            expiryDate = None
            expiry_date_value = row["expiryDate"].strip().lower()
            if expiry_date_value not in {"n/a", ""}:
                try:
                    expiryDate = expiry_date_value
                except ValueError:
                    raise ValueError(f"Invalid date format '{expiry_date_value}'. Use YYYY-MM-DD.")

            # Convert usage limit safely
            usage_limit_value = row["usageLimit"].split()[0] if " " in row["usageLimit"] else row["usageLimit"]
            usageLimit = int(usage_limit_value) if usage_limit_value.isdigit() else 0

            # Create item as dictionary matching the expected format
            item = {
                "itemId": itemId,
                "name": name,
                "width": width,
                "depth": depth,
                "height": height,
                "mass": mass,
                "priority": priority_value,
                "expiryDate": expiryDate,
                "usageLimit": usageLimit,
                "preferredZone": preferredZone
            }

            items.append(item)

        except (ValueError, KeyError) as e:
            errors.append({"row": row_number, "message": str(e)})

    if items:
        try:
            cargo_system.add_items(items)
            log_action("Import Items", f"Imported {len(items)} items successfully.")
            
            # Create both original and temp item files
            items_df = pl.DataFrame(items)
            print(f"Writing to imported_items.csv...")
            items_df.write_csv("imported_items.csv")
            print(f"Writing to temp_imported_items.csv...")
            items_df.write_csv("temp_imported_items.csv")
            
            # Verify files were created
            if os.path.exists("imported_items.csv"):
                print(f"Successfully created imported_items.csv with {len(items)} items")
            else:
                print("Error: imported_items.csv was not created")
                
            if os.path.exists("temp_imported_items.csv"):
                print(f"Successfully created temp_imported_items.csv with {len(items)} items")
            else:
                print("Error: temp_imported_items.csv was not created")
            
        except Exception as e:
            print(f"Error writing files: {str(e)}")
            log_action("Import Items Failed", f"Error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing items: {str(e)}")

    return ImportItemsResponse(
        success=len(errors) == 0,
        items_imported=len(items),
        errors=errors,
        message="Items imported successfully" if len(errors) == 0 else "Some items could not be imported"
    )

### **2. Import Containers from CSV**
@router.post("/import/containers", response_model=ImportContainersResponse)
async def import_containers(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    try:
        contents = await file.read()
        decoded_contents = contents.decode("utf-8").strip()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    if not decoded_contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Validate required columns
    reader = csv.DictReader(io.StringIO(decoded_contents))
    required_columns = {"zone", "containerId", "width", "depth", "height"}

    if not required_columns.issubset(set(reader.fieldnames or [])):
        missing_columns = required_columns - set(reader.fieldnames or [])
        raise HTTPException(status_code=400, detail=f"Missing required columns: {missing_columns}")

    # Convert CSV to JSON
    containers_json = convert_csv_to_json(decoded_contents)

    containers = []
    errors = []

    for row_number, row in enumerate(containers_json, start=1):
        try:
            container = {
                "zone": row["zone"],
                "containerId": row["containerId"],
                "width": float(row["width"]),
                "depth": float(row["depth"]),
                "height": float(row["height"])
            }
            containers.append(container)
        except (ValueError, KeyError) as e:
            errors.append({"row": row_number, "message": str(e)})

    if containers:
        try:
            cargo_system.add_containers(containers)
            log_action("Import Containers", f"Imported {len(containers)} containers successfully.")
            
            # Create both original and temp container files
            containers_df = pl.DataFrame(containers)
            containers_df.write_csv("imported_containers.csv")
            containers_df.write_csv("temp_imported_containers.csv")
            
        except Exception as e:
            log_action("Import Containers Failed", f"Error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing containers: {str(e)}")

    return ImportContainersResponse(
        success=len(errors) == 0,
        containers_imported=len(containers),
        errors=errors,
        message="Containers imported successfully" if len(errors) == 0 else "Some containers could not be imported"
    )

### **3. Export Cargo Arrangement as CSV**
@router.get("/export/arrangement")
async def export_arrangement():
    try:
        print("\n=== Starting Export Process ===")
        
        # If cargo_system is empty, try to load from CSV files directly
        if cargo_system.items_df.is_empty():
            print("Cargo system items are empty. Attempting to load from CSV files...")
            if os.path.exists("imported_items.csv"):
                items_df = pl.read_csv("imported_items.csv")
                if not items_df.is_empty():
                    print(f"Loaded {len(items_df)} items from imported_items.csv")
                    cargo_system.items_df = items_df
                else:
                    print("Error: imported_items.csv exists but is empty")
                    raise HTTPException(status_code=400, detail="No items loaded")
            else:
                print("Error: imported_items.csv does not exist")
                raise HTTPException(status_code=400, detail="No items loaded")
            
        if cargo_system.containers_df.is_empty():
            print("Cargo system containers are empty. Attempting to load from CSV files...")
            if os.path.exists("imported_containers.csv"):
                containers_df = pl.read_csv("imported_containers.csv")
                if not containers_df.is_empty():
                    print(f"Loaded {len(containers_df)} containers from imported_containers.csv")
                    cargo_system.containers_df = containers_df
                else:
                    print("Error: imported_containers.csv exists but is empty")
                    raise HTTPException(status_code=400, detail="No containers loaded")
            else:
                print("Error: imported_containers.csv does not exist")
                raise HTTPException(status_code=400, detail="No containers loaded")
        
        # Verify data is loaded
        if cargo_system.items_df.is_empty():
            print("Error: No items loaded")
            raise HTTPException(status_code=400, detail="No items loaded")
            
        if cargo_system.containers_df.is_empty():
            print("Error: No containers loaded")
            raise HTTPException(status_code=400, detail="No containers loaded")
            
        total_items = len(cargo_system.items_df)
        print(f"Total items to process: {total_items}")
        
        # Group containers by zone
        containers_by_zone = {}
        for container in cargo_system.containers_df.iter_rows(named=True):
            zone = container["zone"]
            if zone not in containers_by_zone:
                containers_by_zone[zone] = []
            containers_by_zone[zone].append({
                "containerId": container["containerId"],
                "width": float(container["width"]),
                "depth": float(container["depth"]),
                "height": float(container["height"]),
                "current_position": {"x": 0, "y": 0, "z": 0},
                "used_volume": 0
            })
        
        # Create direct placements
        placements = []
        
        # Process each item and assign to its preferred zone
        for item in cargo_system.items_df.iter_rows(named=True):
            try:
                zone = item["preferredZone"]
                if zone not in containers_by_zone:
                    print(f"Warning: No containers found for zone {zone}, skipping item {item['itemId']}")
                    continue
                
                # Find the best container in the zone (least used volume)
                best_container = min(
                    containers_by_zone[zone],
                    key=lambda c: c["used_volume"]
                )
                
                current_pos = best_container["current_position"]
                
                # Calculate item placement
                placement = {
                    "itemId": item["itemId"],
                    "zone": zone,
                    "containerId": best_container["containerId"],
                    "start_x_cm": current_pos["x"],
                    "start_y_cm": current_pos["y"],
                    "start_z_cm": current_pos["z"],
                    "end_x_cm": current_pos["x"] + item["width"],
                    "end_y_cm": current_pos["y"] + item["depth"],
                    "end_z_cm": current_pos["z"] + item["height"]
                }
                
                # Update container's current position and used volume
                item_volume = item["width"] * item["depth"] * item["height"]
                best_container["used_volume"] += item_volume
                
                # Update position for next item (simple stacking)
                if current_pos["x"] + item["width"] * 2 <= best_container["width"]:
                    current_pos["x"] += item["width"]
                else:
                    current_pos["x"] = 0
                    if current_pos["y"] + item["depth"] * 2 <= best_container["depth"]:
                        current_pos["y"] += item["depth"]
                    else:
                        current_pos["y"] = 0
                        current_pos["z"] += item["height"]
                
                # Check if container is full
                if current_pos["z"] + item["height"] > best_container["height"]:
                    print(f"Container {best_container['containerId']} in zone {zone} is full")
                    # Mark container as full by setting used_volume to a very high value
                    best_container["used_volume"] = float('inf')
                
                placements.append(placement)
                
            except Exception as e:
                print(f"Error processing item {item['itemId']}: {str(e)}")
                continue
        
        # Create and save the cargo_arrangement.csv file
        arrangement_csv_path = "cargo_arrangement.csv"
        temp_arrangement_csv_path = "temp_cargo_arrangement.csv"
        
        print(f"Writing to {arrangement_csv_path}...")
        with open(arrangement_csv_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["itemId", "zone", "containerId", "coordinates"])
            
            for placement in placements:
                writer.writerow([
                    placement["itemId"],
                    placement["zone"],
                    placement["containerId"],
                    f"({round(placement['start_x_cm'], 2)},{round(placement['start_y_cm'], 2)},{round(placement['start_z_cm'], 2)}),"
                    f"({round(placement['end_x_cm'], 2)},{round(placement['end_y_cm'], 2)},{round(placement['end_z_cm'], 2)})"
                ])

        print(f"Writing to {temp_arrangement_csv_path}...")
        with open(temp_arrangement_csv_path, 'w', newline='') as csvfile:
            writert = csv.writer(csvfile)
            writert.writerow(["itemId", "zone", "containerId", "coordinates"])
            
            for placement in placements:
                writert.writerow([
                    placement["itemId"],
                    placement["zone"],
                    placement["containerId"],
                    f"({round(placement['start_x_cm'], 2)},{round(placement['start_y_cm'], 2)},{round(placement['start_z_cm'], 2)}),"
                    f"({round(placement['end_x_cm'], 2)},{round(placement['end_y_cm'], 2)},{round(placement['end_z_cm'], 2)})"
                ])

        # Verify files were created
        if os.path.exists(arrangement_csv_path):
            print(f"Successfully created {arrangement_csv_path} with {len(placements)} placements")
        else:
            print(f"Error: {arrangement_csv_path} was not created")
            
        if os.path.exists(temp_arrangement_csv_path):
            print(f"Successfully created {temp_arrangement_csv_path} with {len(placements)} placements")
        else:
            print(f"Error: {temp_arrangement_csv_path} was not created")
        
        # Print container usage statistics
        for zone, containers in containers_by_zone.items():
            print(f"\nZone {zone} container usage:")
            for container in containers:
                if container["used_volume"] != float('inf'):
                    total_volume = container["width"] * container["depth"] * container["height"]
                    usage_percentage = (container["used_volume"] / total_volume) * 100
                    print(f"Container {container['containerId']}: {usage_percentage:.2f}% used")
                else:
                    print(f"Container {container['containerId']}: Full")
        
        # Prepare the response
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["itemId", "zone", "containerId", "coordinates"])
        
        with open(arrangement_csv_path, 'r') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip header
            for row in reader:
                writer.writerow(row)
                
        output.seek(0)
        
        print("=== Export Process Complete ===")
        log_action("Export Arrangement", f"Exported {len(placements)} placements successfully")

        return Response(
            output.getvalue(), 
            media_type="text/csv", 
            headers={
                "Content-Disposition": "attachment; filename=cargo_arrangement.csv"
            }
        )
        
    except Exception as e:
        print(f"Export Error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        log_action("Export Failed", f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))