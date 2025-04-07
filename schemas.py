import polars as pl
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Tuple, Any, Union
from datetime import date, datetime
import traceback
import os
import re

class Octant:
    """Represents a node (octant) in the Octree."""
    def __init__(self, x, y, z, width, depth, height, level=0, max_level=3):
        self.x, self.y, self.z = x, y, z
        self.width, self.depth, self.height = width, depth, height
        self.level = level
        self.max_level = max_level
        self.occupied = False
        self.children = None  # If subdivided, this holds 8 sub-octants

    def subdivide(self):
        """Splits the octant into 8 smaller octants if needed."""
        if self.level >= self.max_level:
            return
        half_w, half_d, half_h = self.width / 2, self.depth / 2, self.height / 2
        self.children = [
            Octant(self.x, self.y, self.z, half_w, half_d, half_h, self.level + 1),
            Octant(self.x + half_w, self.y, self.z, half_w, half_d, half_h, self.level + 1),
            Octant(self.x, self.y + half_d, self.z, half_w, half_d, half_h, self.level + 1),
            Octant(self.x + half_w, self.y + half_d, self.z, half_w, half_d, half_h, self.level + 1),
            Octant(self.x, self.y, self.z + half_h, half_w, half_d, half_h, self.level + 1),
            Octant(self.x + half_w, self.y, self.z + half_h, half_w, half_d, half_h, self.level + 1),
            Octant(self.x, self.y + half_d, self.z + half_h, half_w, half_d, half_h, self.level + 1),
            Octant(self.x + half_w, self.y + half_d, self.z + half_h, half_w, half_d, half_h, self.level + 1),
        ]

    def is_fitting(self, item_row):
        """Checks if an item can fit into this octant."""
        return (
            not self.occupied and 
            item_row["width"] <= self.width and 
            item_row["depth"] <= self.depth and 
            item_row["height"] <= self.height
        )

    def place_item(self, item_row):
        """Tries to place an item into the octree."""
        if self.is_fitting(item_row):
            self.occupied = True
            return pl.DataFrame({
                "start_x": [self.x], "start_y": [self.y], "start_z": [self.z],
                "end_x": [self.x + item_row["width"]],
                "end_y": [self.y + item_row["depth"]],
                "end_z": [self.z + item_row["height"]]
            })

        if not self.children:
            self.subdivide()

        for child in self.children:
            result = child.place_item(item_row)
            if result is not None:
                return result

        return None  # No space found

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
            0, 0, 0, container_row["width"], container_row["depth"], container_row["height"]
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
        """Places items using Octree, now indexed by zone."""
        print("\n=== Starting Optimization Process ===")
        
        print(f"Items DataFrame Shape: {self.items_df.shape if not self.items_df.is_empty() else 'Empty'}")
        print(f"Containers DataFrame Shape: {self.containers_df.shape if not self.containers_df.is_empty() else 'Empty'}")
        print(f"Number of Octrees: {len(self.octrees)}")
        
        if self.items_df.is_empty() or self.containers_df.is_empty():
            print("Error: No items or containers available.")
            return pl.DataFrame({"success": [False], "placements": [None], "rearrangements": [None]})

        required_item_cols = ["itemId", "width", "depth", "height", "priority", "preferredZone"]
        missing_cols = [col for col in required_item_cols if col not in self.items_df.columns]
        if missing_cols:
            print(f"Error: Missing required columns in items_df: {missing_cols}")
            return pl.DataFrame({"success": [False], "placements": [None], "rearrangements": [None]})

        default_placements = {
            "itemId": [],
            "zone": [],
            "start_x": [],
            "start_y": [],
            "start_z": [],
            "end_x": [],
            "end_y": [],
            "end_z": []
        }
        placements_df = pl.DataFrame(default_placements)

        print("\n=== Processing Items ===")
        sorted_items_df = self.items_df.sort("priority", descending=True)
        print(f"Total items to process: {len(sorted_items_df)}")

        for item_row in sorted_items_df.iter_rows(named=True):
            print(f"\nProcessing item ID: {item_row['itemId']}")
            
            try:
                preferred_zone = str(item_row["preferredZone"]).strip()
                print(f"Preferred zone: {preferred_zone}")
                
                print(f"Available zones: {list(self.octrees.keys())}")
                
                self.octrees = {str(zone).strip(): octree for zone, octree in self.octrees.items()}
                
                octree = self.octrees.get(preferred_zone)
                if octree is None:
                    print(f"Warning: No octree found for zone '{preferred_zone}'")
                    continue

                if not all(item_row[dim] > 0 for dim in ['width', 'depth', 'height']):
                    print(f"Warning: Invalid dimensions for item {item_row['itemId']}")
                    continue

                print("Attempting placement...")
                placement_position = octree.place_item(item_row)
                print(f"Placement result: {'Success' if placement_position is not None else 'Failed'}")

                if placement_position is not None:
                    placement_record = pl.DataFrame({
                        "itemId": [item_row["itemId"]],
                        "zone": [preferred_zone],
                    }).hstack(placement_position)

                    placements_df = placements_df.vstack(placement_record) if not placements_df.is_empty() else placement_record
                    print(f"Successfully placed item {item_row['itemId']} in zone {preferred_zone}")
                else:
                    print(f"Failed to place item {item_row['itemId']} in zone {preferred_zone}")

            except Exception as e:
                print(f"Error processing item {item_row['itemId']}: {str(e)}")
                continue

        print("\n=== Finalizing Results ===")
        print(f"Total successful placements: {len(placements_df)}")
        
        default_rearrangements = {
            "step": [],
            "action": [],
            "itemId": [],
            "from_container": [],
            "to_container": []
        }
        rearrangements_df = pl.DataFrame(default_rearrangements)

        result = pl.DataFrame({
            "success": [True],
            "placements": [placements_df],
            "rearrangements": [rearrangements_df]
        })
        
        print("=== Optimization Complete ===\n")
        return result

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