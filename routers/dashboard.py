from fastapi import APIRouter
import polars as pl
from datetime import datetime, timedelta
import os

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
)

@router.get("/stats")
async def get_dashboard_stats():
    try:
        print("Fetching dashboard stats...")
        # Check for required files
        item_files = ["imported_items.csv", "temp_imported_items.csv"]
        item_file_path = None
        
        for file_path in item_files:
            if os.path.exists(file_path):
                item_file_path = file_path
                print(f"Using item file: {item_file_path}")
                break
                
        if not item_file_path:
            print("No imported item files found")
            return {
                "success": False,
                "error": "No imported items data found"
            }

        # Read the items data
        print(f"Reading {item_file_path}...")
        items_df = pl.read_csv(item_file_path)
        print(f"Found {len(items_df)} items")
        print(f"Columns: {items_df.columns}")
        
        # Calculate cargo status distribution
        total_items = len(items_df)
        
        # Read cargo arrangement to determine placed items
        arrangement_files = ["cargo_arrangement.csv", "temp_arrangement.csv", "arrangement.csv"]
        arrangement_file_path = None
        
        for file_path in arrangement_files:
            if os.path.exists(file_path):
                arrangement_file_path = file_path
                print(f"Using arrangement file: {arrangement_file_path}")
                break
                
        in_storage = 0
        if arrangement_file_path:
            try:
                print(f"Reading {arrangement_file_path}...")
                cargo_df = pl.read_csv(arrangement_file_path)
                in_storage = len(cargo_df)
                print(f"Found {in_storage} items in storage")
            except Exception as e:
                print(f"Error reading arrangement file: {str(e)}")
                # Continue with in_storage = 0
        else:
            print("No arrangement file found")
        
        # Calculate other statuses
        in_transit = total_items - in_storage  # Items not yet placed are considered in transit
        
        # Calculate retrieved items from item_retrievals.csv
        retrieved = 0
        retrieval_files = ["item_retrievals.csv", "retrievals.csv"]
        retrieval_file_path = None
        
        for file_path in retrieval_files:
            if os.path.exists(file_path):
                retrieval_file_path = file_path
                print(f"Using retrievals file: {retrieval_file_path}")
                break
                
        if retrieval_file_path:
            try:
                print(f"Reading {retrieval_file_path}...")
                retrievals_df = pl.read_csv(retrieval_file_path)
                retrieved = len(retrievals_df)
                print(f"Found {retrieved} retrieved items")
            except Exception as e:
                print(f"Error reading retrievals file: {str(e)}")
                retrieved = 0
        else:
            print("No retrievals file found")
            
        # Calculate expired items from waste_items.csv
        expired = 0
        waste_files = ["waste_items.csv", "wasted_items.csv"]
        waste_file_path = None
        
        for file_path in waste_files:
            if os.path.exists(file_path):
                waste_file_path = file_path
                print(f"Using waste file: {waste_file_path}")
                break
                
        if waste_file_path:
            try:
                print(f"Reading {waste_file_path}...")
                waste_df = pl.read_csv(waste_file_path)
                
                # Check if there's a status or type column
                status_column = None
                for col in waste_df.columns:
                    if "status" in col.lower() or "type" in col.lower() or "reason" in col.lower():
                        status_column = col
                        break
                
                if status_column:
                    # Count items specifically marked as EXPIRED
                    expired = waste_df.filter(pl.col(status_column).str.to_lowercase().str.contains("expire")).height
                    print(f"Found {expired} expired items")
                else:
                    # If no status column, count all waste items as expired
                    expired = len(waste_df)
                    print(f"No status column found, counting all {expired} waste items as expired")
            except Exception as e:
                print(f"Error reading waste file: {str(e)}")
                expired = 0
        else:
            print("No waste file found")

        print(f"Status counts - In Storage: {in_storage}, In Transit: {in_transit}, Retrieved: {retrieved}, Expired: {expired}")
        
        # Calculate container fullness
        container_files = ["imported_containers.csv", "containers.csv", "temp_imported_containers.csv"]
        container_file_path = None
        
        for file_path in container_files:
            if os.path.exists(file_path):
                container_file_path = file_path
                print(f"Using container file: {container_file_path}")
                break
        
        # Default values if containers file not found
        full_containers = 0
        partially_full_containers = 0
        empty_containers = 0
        total_containers = 0
        
        if container_file_path:
            try:
                containers_df = pl.read_csv(container_file_path)
                total_containers = len(containers_df)
                print(f"Found {total_containers} containers")
                
                if arrangement_file_path:
                    # Calculate which containers have items in them
                    cargo_df = pl.read_csv(arrangement_file_path)
                    
                    # Get unique container IDs from the arrangement
                    if "containerId" in cargo_df.columns:
                        container_column = "containerId"
                    elif "container_id" in cargo_df.columns:
                        container_column = "container_id"
                    else:
                        # Try to find the container column
                        for col in cargo_df.columns:
                            if "container" in col.lower():
                                container_column = col
                                break
                        else:
                            print("No container ID column found in arrangement file")
                            container_column = None
                    
                    if container_column:
                        # Count items per container
                        container_counts = {}
                        for container_id in cargo_df[container_column]:
                            container_counts[container_id] = container_counts.get(container_id, 0) + 1
                        
                        print(f"Container item counts: {container_counts}")
                        
                        # Calculate container usage based on item counts
                        # For this example, we'll consider:
                        # - Full: 10+ items
                        # - Partially full: 1-9 items
                        # - Empty: 0 items
                        
                        used_containers = len(container_counts)
                        for container_id, item_count in container_counts.items():
                            if item_count >= 10:
                                full_containers += 1
                            else:
                                partially_full_containers += 1
                        
                        empty_containers = total_containers - used_containers
                        
                        print(f"Full containers: {full_containers}")
                        print(f"Partially full containers: {partially_full_containers}")
                        print(f"Empty containers: {empty_containers}")
                    else:
                        # Default to all containers empty if no container column found
                        empty_containers = total_containers
                else:
                    # If no arrangement file, all containers are empty
                    empty_containers = total_containers
            except Exception as e:
                print(f"Error processing container data: {str(e)}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                # Set default values
                empty_containers = total_containers
        else:
            print("No container file found")
            # Use mock data for containers if no container file is found
            print("Using mock container data")
            total_containers = 5  # Mock total containers
            full_containers = 1
            partially_full_containers = 2
            empty_containers = 2

        # Calculate monthly arrivals using current data
        current_month = datetime.now().month
        monthly_arrivals = [
            total_items if i == current_month - 1 else 0
            for i in range(12)
        ]
        
        print(f"Monthly arrivals: {monthly_arrivals}")

        # Calculate weight trends (last 7 days)
        dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
        
        # Calculate total mass per day (simulated for now)
        # In a real system, this would come from historical data
        mass_column = None
        weight_column = None
        
        # Find the appropriate column name
        for col in items_df.columns:
            if col.lower() == "mass":
                mass_column = col
                break
            elif "weight" in col.lower():
                weight_column = col
        
        base_mass = 0
        if mass_column:
            try:
                base_mass = float(items_df[mass_column].sum())
                print(f"Total mass calculated: {base_mass} from column '{mass_column}'")
            except Exception as e:
                print(f"Error calculating mass: {str(e)}")
                print(f"Mass column data: {items_df[mass_column]}")
        elif weight_column:
            try:
                base_mass = float(items_df[weight_column].sum())
                print(f"Using weight column instead, total: {base_mass} from column '{weight_column}'")
            except Exception as e:
                print(f"Error calculating weight: {str(e)}")
        else:
            print(f"No mass or weight column found! Available columns: {items_df.columns}")
            # Mock data
            base_mass = len(items_df) * 10  # assume 10kg per item
            print(f"Using mock mass data: {base_mass}")
        
        weight_data = {
            "labels": dates,
            "data": [
                round(base_mass * (1 - i/20), 2)  # Simulated decreasing trend
                for i in range(7)
            ]
        }

        response_data = {
            "success": True,
            "inStorage": in_storage,
            "inTransit": in_transit,
            "retrieved": retrieved,
            "expired": expired,
            "fullContainers": full_containers,
            "partiallyFullContainers": partially_full_containers,
            "emptyContainers": empty_containers,
            "totalContainers": total_containers,
            "monthlyArrivals": monthly_arrivals,
            "weightTrends": weight_data
        }
        print("Returning response:", response_data)
        return response_data

    except Exception as e:
        print(f"Dashboard Error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e)
        } 