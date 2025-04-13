import polars as pl
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Tuple, Any, Union
from datetime import date, datetime
import traceback
import os
import re

class Octant:
    """Represents a node (octant) in the Octree."""
    def __init__(self, x, y, z, width, depth, height, level=0, max_level=4):
        self.x, self.y, self.z = x, y, z
        self.width, self.depth, self.height = width, depth, height
        self.level = level
        self.max_level = max_level
        self.occupied = False
        self.children = None  # If subdivided, this holds 8 sub-octants
        self.item = None  # Store the item that occupies this space

    def subdivide(self):
        """Splits the octant into 8 smaller octants if needed."""
        if self.level >= self.max_level:
            return
        half_w, half_d, half_h = self.width / 2, self.depth / 2, self.height / 2
        self.children = [
            Octant(self.x, self.y, self.z, half_w, half_d, half_h, self.level + 1, self.max_level),
            Octant(self.x + half_w, self.y, self.z, half_w, half_d, half_h, self.level + 1, self.max_level),
            Octant(self.x, self.y + half_d, self.z, half_w, half_d, half_h, self.level + 1, self.max_level),
            Octant(self.x + half_w, self.y + half_d, self.z, half_w, half_d, half_h, self.level + 1, self.max_level),
            Octant(self.x, self.y, self.z + half_h, half_w, half_d, half_h, self.level + 1, self.max_level),
            Octant(self.x + half_w, self.y, self.z + half_h, half_w, half_d, half_h, self.level + 1, self.max_level),
            Octant(self.x, self.y + half_d, self.z + half_h, half_w, half_d, half_h, self.level + 1, self.max_level),
            Octant(self.x + half_w, self.y + half_d, self.z + half_h, half_w, half_d, half_h, self.level + 1, self.max_level),
        ]

    def is_fitting(self, item_row):
        """Checks if an item can fit into this octant."""
        if self.occupied:
            return False
            
        item_width = float(item_row["width"])
        item_depth = float(item_row["depth"])
        item_height = float(item_row["height"])
        
        # Check if item dimensions fit within this octant
        return (item_width <= self.width and 
                item_depth <= self.depth and 
                item_height <= self.height)

    def place_item(self, item_row):
        """Tries to place an item into the octree."""
        # If this octant is already occupied, try to subdivide
        if self.occupied:
            if not self.children:
                self.subdivide()
            if self.children:
                for child in self.children:
                    result = child.place_item(item_row)
                    if result is not None:
                        return result
            return None

        # Check if item fits in this octant
        if self.is_fitting(item_row):
            # Place the item here
            self.occupied = True
            self.item = item_row
            return pl.DataFrame({
                "start_x": [self.x], "start_y": [self.y], "start_z": [self.z],
                "end_x": [self.x + float(item_row["width"])],
                "end_y": [self.y + float(item_row["depth"])],
                "end_z": [self.z + float(item_row["height"])]
            })

        # If item doesn't fit and we haven't reached max level, try to subdivide
        if self.level < self.max_level:
            if not self.children:
                self.subdivide()
            if self.children:
                for child in self.children:
                    result = child.place_item(item_row)
                    if result is not None:
                        return result

        return None

class Object3D:
    def __init__(self, itemId, name, containerId, start, end):
        self.itemId = itemId
        self.name = name
        self.containerId = containerId
        self.start = start
        self.end = end
        self.front_z = min(start['height'], end['height'])

class Octree:
    """Octree structure for managing storage placement."""
    def __init__(self, container_row):
        self.root = Octant(
            0, 0, 0, 
            float(container_row["width"]), 
            float(container_row["depth"]), 
            float(container_row["height"]),
            max_level=5  # Increased max level for finer granularity
        )

    def place_item(self, item_row):
        """Finds the best space for an item and places it."""
        return self.root.place_item(item_row)

class Coordinates(BaseModel):
    width: float
    depth: float
    height: float

class Position(BaseModel):
    startCoordinates: Coordinates
    endCoordinates: Coordinates

class ItemPlacement(BaseModel):
    itemId: Union[int, str]
    containerId: str
    position: Position
    
    @validator('itemId')
    def validate_item_id(cls, v):
        if isinstance(v, int):
            return v
        # Extract numeric part from strings like "test-item-1"
        if isinstance(v, str):
            # Try to extract the last number from the string
            match = re.search(r'(\d+)$', v)
            if match:
                return int(match.group(1))
            # If no match found, try to convert the whole string to int
            try:
                return int(v)
            except ValueError:
                pass
        raise ValueError('Invalid itemId format, must be an integer or a string ending with digits')

class RetrievalStep(BaseModel):
    step: int
    action: str
    itemId: Union[int, str]
    item_name: str
    
    @validator('itemId')
    def validate_item_id(cls, v):
        if isinstance(v, int):
            return v
        # Extract numeric part from strings like "test-item-1"
        if isinstance(v, str):
            # Try to extract the last number from the string
            match = re.search(r'(\d+)$', v)
            if match:
                return int(match.group(1))
            # If no match found, try to convert the whole string to int
            try:
                return int(v)
            except ValueError:
                pass
        raise ValueError('Invalid itemId format, must be an integer or a string ending with digits')

class RearrangementStep(BaseModel):
    step: int
    action: str  # "move", "remove", "place"
    itemId: Union[int, str]
    from_container: str
    from_position: Position
    to_container: Optional[str] = None
    to_position: Optional[Position] = None
    
    @validator('itemId')
    def validate_item_id(cls, v):
        if isinstance(v, int):
            return v
        # Extract numeric part from strings like "test-item-1"
        if isinstance(v, str):
            # Try to extract the last number from the string
            match = re.search(r'(\d+)$', v)
            if match:
                return int(match.group(1))
            # If no match found, try to convert the whole string to int
            try:
                return int(v)
            except ValueError:
                pass
        raise ValueError('Invalid itemId format, must be an integer or a string ending with digits')

from pydantic import BaseModel, Field

class Item(BaseModel):
    itemId: Union[int, str]
    name: str
    width: float
    depth: float
    height: float
    mass: float
    priority: int
    preferredZone: str
    expiryDate: Optional[str] = None
    usageLimit: Optional[int] = None
    
    @validator('itemId')
    def validate_item_id(cls, v):
        if isinstance(v, int):
            return v
        # Extract numeric part from strings like "test-item-1"
        if isinstance(v, str):
            # Try to extract the last number from the string
            match = re.search(r'(\d+)$', v)
            if match:
                return int(match.group(1))
            # If no match found, try to convert the whole string to int
            try:
                return int(v)
            except ValueError:
                pass
        raise ValueError('Invalid itemId format, must be an integer or a string ending with digits')

class Container(BaseModel):
    containerId: str
    zone: str
    width: float
    depth: float
    height: float

class ItemForPlacement(BaseModel):
    itemId: str
    name: str
    width: float
    depth: float
    height: float
    mass: float
    priority: int
    preferredZone: str  # Zone

class PlacementRequest(BaseModel):
    items: List[ItemForPlacement]
    containers: List[Container]

class PlacementResponse(BaseModel):
    success: bool
    placements: List[ItemPlacement]
    rearrangements: List[RearrangementStep]

class Item_for_search(BaseModel):
    itemId: Union[int, str]
    name: str
    containerId: str
    zone: str
    position: Position
    
    @validator('itemId')
    def validate_item_id(cls, v):
        if isinstance(v, int):
            return v
        # Extract numeric part from strings like "test-item-1"
        if isinstance(v, str):
            # Try to extract the last number from the string
            match = re.search(r'(\d+)$', v)
            if match:
                return int(match.group(1))
            # If no match found, try to convert the whole string to int
            try:
                return int(v)
            except ValueError:
                pass
        raise ValueError('Invalid itemId format, must be an integer or a string ending with digits')

class RetrieveItemRequest(BaseModel):
    itemId: Union[int, str]
    userId: str
    timestamp: Optional[str] = None
    
    @validator('itemId')
    def validate_item_id(cls, v):
        if isinstance(v, int):
            return v
        # Extract numeric part from strings like "test-item-1"
        if isinstance(v, str):
            # Try to extract the last number from the string
            match = re.search(r'(\d+)$', v)
            if match:
                return int(match.group(1))
            # If no match found, try to convert the whole string to int
            try:
                return int(v)
            except ValueError:
                pass
        raise ValueError('Invalid itemId format, must be an integer or a string ending with digits')

class PlaceItemRequest(BaseModel):
    itemId: Union[int, str]
    containerId: str
    position: Position
    timestamp: Optional[str] = None
    
    @validator('itemId')
    def validate_item_id(cls, v):
        if isinstance(v, int):
            return v
        # Extract numeric part from strings like "test-item-1"
        if isinstance(v, str):
            # Try to extract the last number from the string
            match = re.search(r'(\d+)$', v)
            if match:
                return int(match.group(1))
            # If no match found, try to convert the whole string to int
            try:
                return int(v)
            except ValueError:
                pass
        raise ValueError('Invalid itemId format, must be an integer or a string ending with digits')

class PlaceItemResponse(BaseModel):
    success: bool

class ImportItemsResponse(BaseModel):
    success: bool
    items_imported: int
    errors: List[Dict[str, Any]]
    message: str

class ImportContainersResponse(BaseModel):
    success: bool
    containers_imported: int
    errors: List[Dict[str, Any]]
    message: str

class CargoArrangementExport(BaseModel):
    itemId: Union[int, str]
    zone: str
    containerId: str
    coordinates: str
    
    @validator('itemId')
    def validate_item_id(cls, v):
        if isinstance(v, int):
            return v
        # Extract numeric part from strings like "test-item-1"
        if isinstance(v, str):
            # Try to extract the last number from the string
            match = re.search(r'(\d+)$', v)
            if match:
                return int(match.group(1))
            # If no match found, try to convert the whole string to int
            try:
                return int(v)
            except ValueError:
                pass
        raise ValueError('Invalid itemId format, must be an integer or a string ending with digits')

class CargoPlacementSystem:
    def __init__(self):
        self.items_df = pl.DataFrame()
        self.containers_df = pl.DataFrame()
        self.cargo_df = pl.DataFrame()
        self.octrees = {}
        self.loading_log = []

    def add_items(self, items: List[Dict[str, Any]]):
        new_items_df = pl.DataFrame(items)
        if self.items_df.is_empty():
            self.items_df = new_items_df
        else:
            self.items_df = pl.concat([self.items_df, new_items_df], how="vertical")

    def add_containers(self, containers: List[Dict[str, Any]]):
        new_containers_df = pl.DataFrame(containers)
        if self.containers_df.is_empty():
            self.containers_df = new_containers_df
        else:
            self.containers_df = pl.concat([self.containers_df, new_containers_df], how="vertical")

    def load_from_csv(self, items_path: str, containers_path: str):
        self.loading_log.append("Loading CSV data...")

        try:
            if os.path.exists(items_path) and os.path.getsize(items_path) > 0:
                self.items_df = pl.read_csv(items_path)
                self.loading_log.append("Items data loaded successfully.")

            if os.path.exists(containers_path) and os.path.getsize(containers_path) > 0:
                self.containers_df = pl.read_csv(containers_path)
                self.loading_log.append("Containers data loaded successfully.")

        except Exception as e:
            self.loading_log.append(f"Error loading data: {str(e)}")
            self.loading_log.append(traceback.format_exc())

    def optimize_placement(self):
        """Fast bin-packing algorithm for item placement with size matching."""
        if self.items_df.is_empty() or self.containers_df.is_empty():
            return pl.DataFrame()

        # Group containers by zone and sort by volume
        containers_by_zone = {}
        for container_row in self.containers_df.iter_rows(named=True):
            zone = container_row["zone"]
            if zone not in containers_by_zone:
                containers_by_zone[zone] = []
            
            # Calculate container volume
            width = float(container_row["width"])
            depth = float(container_row["depth"])
            height = float(container_row["height"])
            volume = width * depth * height
            
            containers_by_zone[zone].append({
                "container_id": container_row["containerId"],
                "width": width,
                "depth": depth,
                "height": height,
                "volume": volume,
                "row": container_row
            })
        
        # Sort containers by volume within each zone (smallest to largest)
        for zone in containers_by_zone:
            containers_by_zone[zone].sort(key=lambda c: c["volume"])
        
        # Calculate item volumes and sort by priority (highest first)
        items_with_volume = self.items_df.with_columns(
            (pl.col("width") * pl.col("depth") * pl.col("height")).alias("volume")
        ).sort(
            by=["priority"],
            descending=[True]
        )
        
        # Track container usage and occupied spaces
        container_usage = {}
        for container_row in self.containers_df.iter_rows(named=True):
            container_id = container_row["containerId"]
            container_usage[container_id] = {
                "width": float(container_row["width"]),
                "depth": float(container_row["depth"]),
                "height": float(container_row["height"]),
                "occupied_spaces": []  # List of (start_x, start_y, start_z, end_x, end_y, end_z)
            }
        
        # Create a DataFrame to store all placements
        placements_data = []
        unplaced_items = []
        
        # Process items
        for item_row in items_with_volume.iter_rows(named=True):
            preferred_zone = str(item_row["preferredZone"]).strip()
            
            # Skip if no containers in preferred zone
            if preferred_zone not in containers_by_zone:
                unplaced_items.append({
                    "itemId": item_row["itemId"],
                    "name": item_row.get("name", "Unknown"),
                    "reason": f"No containers in zone {preferred_zone}"
                })
                continue
                
            item_width = float(item_row["width"])
            item_depth = float(item_row["depth"])
            item_height = float(item_row["height"])
            item_volume = item_width * item_depth * item_height
            
            # Calculate average container volume in this zone
            zone_containers = containers_by_zone[preferred_zone]
            avg_zone_volume = sum(c["volume"] for c in zone_containers) / len(zone_containers)
            
            # Determine if this is a small or large item relative to zone average
            is_small_item = item_volume < avg_zone_volume
            
            # Try to place in containers of the preferred zone
            placed = False
            
            # For small items, try smallest containers first
            # For large items, try largest containers first
            container_order = zone_containers if is_small_item else list(reversed(zone_containers))
            
            for container_info in container_order:
                container_id = container_info["container_id"]
                usage = container_usage[container_id]
                
                # Try to find a valid position in this container
                for start_x in range(0, int(usage["width"] - item_width) + 1):
                    for start_y in range(0, int(usage["depth"] - item_depth) + 1):
                        for start_z in range(0, int(usage["height"] - item_height) + 1):
                            # Calculate end coordinates
                            end_x = start_x + item_width
                            end_y = start_y + item_depth
                            end_z = start_z + item_height
                            
                            # Check if this position overlaps with any existing items
                            position_valid = True
                            for space in usage["occupied_spaces"]:
                                # Check for overlap in all dimensions
                                if not (end_x <= space[0] or start_x >= space[3] or
                                       end_y <= space[1] or start_y >= space[4] or
                                       end_z <= space[2] or start_z >= space[5]):
                                    position_valid = False
                                    break
                            
                            if position_valid:
                                # Place the item here
                                usage["occupied_spaces"].append((start_x, start_y, start_z, end_x, end_y, end_z))
                                
                                # Create placement record
                                placement_record = {
                                    "itemId": item_row["itemId"],
                                    "zone": preferred_zone,
                                    "containerId": container_id,
                                    "coordinates": f"({start_x},{start_y},{start_z}),({end_x},{end_y},{end_z})"
                                }
                                placements_data.append(placement_record)
                                placed = True
                                break
                            
                        if placed:
                            break
                    if placed:
                        break
                if placed:
                    break
            
            # If item couldn't be placed, mark as unplaced
            if not placed:
                unplaced_items.append({
                    "itemId": item_row["itemId"],
                    "name": item_row.get("name", "Unknown"),
                    "dimensions": f"{item_width}x{item_depth}x{item_height}",
                    "preferredZone": preferred_zone,
                    "reason": "No suitable container in preferred zone"
                })
        
        # Create placements DataFrame
        placements_df = pl.DataFrame(placements_data)
        
        # Save placements to CSV
        if not placements_df.is_empty():
            try:
                if os.path.exists("cargo_arrangement.csv") and os.path.getsize("cargo_arrangement.csv") > 0:
                    existing_df = pl.read_csv("cargo_arrangement.csv")
                    combined_df = pl.concat([existing_df, placements_df], how="vertical")
                    combined_df.write_csv("cargo_arrangement.csv")
                else:
                    placements_df.write_csv("cargo_arrangement.csv")
            except Exception as e:
                print(f"Error saving to cargo_arrangement.csv: {str(e)}")
        
        print(f"\nPlacement Summary:")
        print(f"Total items processed: {len(items_with_volume)}")
        print(f"Successfully placed: {len(placements_data)}")
        print(f"Failed to place: {len(unplaced_items)}")
        
        return placements_df

class CargoClassificationSystem:
    def __init__(self):
        self.items_df = pl.DataFrame()
        self.containers_df = pl.DataFrame()
        self.octrees = {}
        self.loading_log = []

    def add_classified_items(self, items: List[dict]):
        if not items:
            return
        new_df = pl.DataFrame(items)
        self.items_df = self.items_df.vstack(new_df) if not self.items_df.is_empty() else new_df

class TimeSimulationRequest(BaseModel):
    numOfDays: Optional[int] = None
    toTimestamp: Optional[str] = None
    itemsToBeUsedPerDay: Optional[List[Dict[str, str]]] = None

class ItemModel(BaseModel):
    itemId: Union[int, str]
    name: str
    width: float
    depth: float
    height: float
    mass: float
    priority: int
    expiryDate: Optional[date] = None
    usageLimit: int
    preferredZone: str
    
    @validator('itemId')
    def validate_item_id(cls, v):
        if isinstance(v, int):
            return v
        # Extract numeric part from strings like "test-item-1"
        if isinstance(v, str):
            # Try to extract the last number from the string
            match = re.search(r'(\d+)$', v)
            if match:
                return int(match.group(1))
            # If no match found, try to convert the whole string to int
            try:
                return int(v)
            except ValueError:
                pass
        raise ValueError('Invalid itemId format, must be an integer or a string ending with digits')

class ContainerModel(BaseModel):
    zone: str
    containerId: int
    width: float
    depth: float
    height: float

class ReturnPlanRequest(BaseModel):
    undocking_container_id: str
    undocking_date: str
    max_weight: float

class CompleteUndockingRequest(BaseModel):
    undocking_container_id: str
    timestamp: str

class WasteItem(BaseModel):
    itemId: Union[int, str]
    name: str
    reason: str
    containerId: str
    position: Position
    
    @validator('itemId')
    def validate_item_id(cls, v):
        if isinstance(v, int):
            return v
        # Extract numeric part from strings like "test-item-1"
        if isinstance(v, str):
            # Try to extract the last number from the string
            match = re.search(r'(\d+)$', v)
            if match:
                return int(match.group(1))
            # If no match found, try to convert the whole string to int
            try:
                return int(v)
            except ValueError:
                pass
        raise ValueError('Invalid itemId format, must be an integer or a string ending with digits')

class WasteItemResponse(BaseModel):
    success: bool
    waste_items: List[WasteItem] = []

class WasteItemRequest(BaseModel):
    itemId: Union[int, str]
    name: str
    reason: str
    containerId: str
    position: str
    
    @validator('itemId')
    def validate_item_id(cls, v):
        if isinstance(v, int):
            return v
        # Extract numeric part from strings like "test-item-1"
        if isinstance(v, str):
            # Try to extract the last number from the string
            match = re.search(r'(\d+)$', v)
            if match:
                return int(match.group(1))
            # If no match found, try to convert the whole string to int
            try:
                return int(v)
            except ValueError:
                pass
        raise ValueError('Invalid itemId format, must be an integer or a string ending with digits')

class ReturnPlanStep(BaseModel):
    step: int
    itemId: Union[int, str]
    item_name: str
    from_container: str
    to_container: str
    
    @validator('itemId')
    def validate_item_id(cls, v):
        if isinstance(v, int):
            return v
        # Extract numeric part from strings like "test-item-1"
        if isinstance(v, str):
            # Try to extract the last number from the string
            match = re.search(r'(\d+)$', v)
            if match:
                return int(match.group(1))
            # If no match found, try to convert the whole string to int
            try:
                return int(v)
            except ValueError:
                pass
        raise ValueError('Invalid itemId format, must be an integer or a string ending with digits')

class ReturnItem(BaseModel):
    itemId: Union[int, str]
    name: str
    reason: str
    
    @validator('itemId')
    def validate_item_id(cls, v):
        if isinstance(v, int):
            return v
        # Extract numeric part from strings like "test-item-1"
        if isinstance(v, str):
            # Try to extract the last number from the string
            match = re.search(r'(\d+)$', v)
            if match:
                return int(match.group(1))
            # If no match found, try to convert the whole string to int
            try:
                return int(v)
            except ValueError:
                pass
        raise ValueError('Invalid itemId format, must be an integer or a string ending with digits')

class ReturnManifest(BaseModel):
    undocking_container_id: str
    undocking_date: str
    return_items: List[ReturnItem]
    total_volume: float
    total_weight: float

class ReturnPlanResponse(BaseModel):
    success: bool
    return_plan: List[ReturnPlanStep]
    retrieval_steps: List[RetrievalStep]
    return_manifest: ReturnManifest

class RetrieveResponse(BaseModel):
    success: bool

class SearchResponse(BaseModel):
    success: bool
    found: bool
    item: Optional[Item_for_search] = None
    retrieval_steps: List[RetrievalStep] = []