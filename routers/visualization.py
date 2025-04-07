from fastapi import APIRouter, Query, HTTPException
import polars as pl
import os
from typing import Dict, List, Optional, Any

router = APIRouter(
    prefix="/api/visualization",
    tags=["visualization"],
)

@router.get("/containers")
async def get_container_items(containerId: Optional[str] = None):
    """
    Get container and item data for 3D visualization.
    If containerId is provided, returns data for only that container.
    """
    try:
        # Check if cargo arrangement file exists
        arrangement_files = ["cargo_arrangement.csv", "temp_arrangement.csv", "arrangement.csv"]
        arrangement_file_path = None
        
        for file_path in arrangement_files:
            if os.path.exists(file_path):
                arrangement_file_path = file_path
                print(f"Using arrangement file: {arrangement_file_path}")
                break
                
        if not arrangement_file_path:
            return {"success": False, "error": "No cargo arrangement data found"}
        
        # Read container data
        container_files = ["imported_containers.csv", "containers.csv"]
        container_file_path = None
        
        for file_path in container_files:
            if os.path.exists(file_path):
                container_file_path = file_path
                print(f"Using container file: {container_file_path}")
                break
                
        if not container_file_path:
            return {"success": False, "error": "No container data found"}
        
        # Read the files
        arrangement_df = pl.read_csv(arrangement_file_path)
        containers_df = pl.read_csv(container_file_path)
        
        print(f"Arrangement columns: {arrangement_df.columns}")
        print(f"Container columns: {containers_df.columns}")
        
        # Find the container ID column in arrangement file
        container_id_col = None
        for col in arrangement_df.columns:
            if "container" in col.lower() and "id" in col.lower():
                container_id_col = col
                break
        
        if not container_id_col:
            print("No container ID column found in arrangement file, trying alternative names")
            for col in arrangement_df.columns:
                if "container" in col.lower():
                    container_id_col = col
                    break
        
        if not container_id_col:
            return {"success": False, "error": "No container ID column found in arrangement data"}
        
        # Find relevant dimension columns in containers file
        width_col = next((col for col in containers_df.columns if "width" in col.lower()), None)
        height_col = next((col for col in containers_df.columns if "height" in col.lower()), None)
        depth_col = next((col for col in containers_df.columns if "depth" in col.lower()), None)
        container_id_col_containers = next((col for col in containers_df.columns if "container" in col.lower() and "id" in col.lower()), None)
        
        if not all([width_col, height_col, depth_col, container_id_col_containers]):
            return {"success": False, "error": "Missing required dimension columns in container data"}
        
        # Get coordinates from arrangement data
        coordinates_col = next((col for col in arrangement_df.columns if "coordinate" in col.lower()), None)
        
        # Process container data
        unique_containers = arrangement_df[container_id_col].unique().to_list()
        
        # Filter by containerId if provided
        if containerId and containerId in unique_containers:
            unique_containers = [containerId]
        
        result_data = {
            "success": True,
            "containers": unique_containers,
            "items": {},
            "dimensions": {}
        }
        
        # Get dimensions for each container
        for container_id in unique_containers:
            container_info = containers_df.filter(pl.col(container_id_col_containers) == container_id)
            if len(container_info) > 0:
                result_data["dimensions"][container_id] = {
                    "width": float(container_info[width_col][0]),
                    "height": float(container_info[height_col][0]),
                    "depth": float(container_info[depth_col][0])
                }
            else:
                # Default dimensions if container not found
                result_data["dimensions"][container_id] = {
                    "width": 100.0,
                    "height": 100.0,
                    "depth": 100.0
                }
        
        # Process items for each container
        for container_id in unique_containers:
            container_items = arrangement_df.filter(pl.col(container_id_col) == container_id)
            processed_items = []
            
            for row in container_items.iter_rows(named=True):
                item_id = str(row.get("itemId", "unknown"))
                
                # Parse coordinates if available
                if coordinates_col and coordinates_col in row:
                    coords_str = row[coordinates_col]
                    # Try to parse coordinates in format "(x,y,z),(x,y,z)"
                    try:
                        # Split by comma and extract numbers
                        parts = coords_str.replace('(', '').replace(')', '').split(',')
                        if len(parts) >= 6:
                            start_width_cm = float(parts[0])
                            start_depth_cm = float(parts[1])
                            start_height_cm = float(parts[2])
                            end_width_cm = float(parts[3])
                            end_depth_cm = float(parts[4])
                            end_height_cm = float(parts[5])
                        else:
                            # Default values if parsing fails
                            start_width_cm, start_depth_cm, start_height_cm = 0, 0, 0
                            end_width_cm, end_depth_cm, end_height_cm = 20, 20, 20
                    except Exception as e:
                        print(f"Error parsing coordinates: {e}")
                        # Default values
                        start_width_cm, start_depth_cm, start_height_cm = 0, 0, 0
                        end_width_cm, end_depth_cm, end_height_cm = 20, 20, 20
                else:
                    # If no coordinates column, use separate columns if available
                    start_width_cm = float(row.get("start_width_cm", row.get("startX", 0)))
                    start_depth_cm = float(row.get("start_depth_cm", row.get("startY", 0)))
                    start_height_cm = float(row.get("start_height_cm", row.get("startZ", 0)))
                    end_width_cm = float(row.get("end_width_cm", row.get("endX", 20)))
                    end_depth_cm = float(row.get("end_depth_cm", row.get("endY", 20)))
                    end_height_cm = float(row.get("end_height_cm", row.get("endZ", 20)))
                
                processed_items.append({
                    "item_id": item_id,
                    "start_width_cm": start_width_cm,
                    "start_depth_cm": start_depth_cm,
                    "start_height_cm": start_height_cm,
                    "end_width_cm": end_width_cm,
                    "end_depth_cm": end_depth_cm,
                    "end_height_cm": end_height_cm,
                    "name": row.get("name", f"Item {item_id}")
                })
            
            result_data["items"][container_id] = processed_items
        
        return result_data
        
    except Exception as e:
        import traceback
        print(f"Error in visualization API: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e)) 