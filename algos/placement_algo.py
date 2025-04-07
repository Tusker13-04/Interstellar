from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Tuple, Union
import numpy as np
from datetime import datetime
import polars as pl
import csv
from collections import defaultdict

@dataclass
class OctreeNode:
    center: np.ndarray
    size: float
    children: List['OctreeNode']
    occupied: bool = False
    itemId: Optional[str] = None
    rotation: Optional[str] = None
    priority: Optional[int] = None
    depth: int = 0

@dataclass
class Position3D:
    x: int
    y: int
    z: int

@dataclass
class ItemDimensions:
    width: float
    depth: float
    height: float
    mass: float
    priority: int
    itemId: Optional[Union[str, int]] = None

class Rotation(Enum):
    NO_ROTATION = "NO_ROTATION"
    ROTATE_X = "ROTATE_X"
    ROTATE_Y = "ROTATE_Y"
    ROTATE_Z = "ROTATE_Z"

# Add CSV caching at the module level
_CSV_CACHE = {}

def load_csv(filename):
    """Optimized CSV loading with caching"""
    if filename not in _CSV_CACHE:
        try:
            _CSV_CACHE[filename] = pl.read_csv(filename).to_dicts()
        except Exception as e:
            print(f"Error loading CSV {filename}: {str(e)}")
            _CSV_CACHE[filename] = {}
    return _CSV_CACHE[filename]

class SparseMatrix:
    """Optimized Sparse 3D matrix implementation using spatial partitioning"""
    def __init__(self, width, depth, height, grid_size=10):
        self.width = int(width)
        self.depth = int(depth)
        self.height = int(height)
        self.grid_size = grid_size
        # Use a dictionary of sets for better performance
        self.grid = defaultdict(set)
        self.occupied_cells = set()
        # Track item positions
        self.item_positions = {}

    def _get_grid_cell(self, x, y, z):
        return (x // self.grid_size, y // self.grid_size, z // self.grid_size)

    def is_occupied(self, x_start, y_start, z_start, x_end, y_end, z_end):
        """Optimized occupancy check using grid-based spatial partitioning"""
        # Get grid cells that this region spans
        start_cell = self._get_grid_cell(x_start, y_start, z_start)
        end_cell = self._get_grid_cell(x_end, y_end, z_end)
        
        # Check only the relevant grid cells
        for x in range(start_cell[0], end_cell[0] + 1):
            for y in range(start_cell[1], end_cell[1] + 1):
                for z in range(start_cell[2], end_cell[2] + 1):
                    if (x, y, z) in self.grid and self.grid[(x, y, z)]:
                        return True
        return False

    def occupy(self, x_start, y_start, z_start, x_end, y_end, z_end):
        """Optimized occupation marking using grid-based spatial partitioning"""
        start_cell = self._get_grid_cell(x_start, y_start, z_start)
        end_cell = self._get_grid_cell(x_end, y_end, z_end)
        
        for x in range(start_cell[0], end_cell[0] + 1):
            for y in range(start_cell[1], end_cell[1] + 1):
                for z in range(start_cell[2], end_cell[2] + 1):
                    self.grid[(x, y, z)].add((x_start, y_start, z_start, x_end, y_end, z_end))
                    self.occupied_cells.add((x, y, z))

    def clear(self, x_start, y_start, z_start, x_end, y_end, z_end):
        """Clear a region from the grid"""
        start_cell = self._get_grid_cell(x_start, y_start, z_start)
        end_cell = self._get_grid_cell(x_end, y_end, z_end)
        
        for x in range(start_cell[0], end_cell[0] + 1):
            for y in range(start_cell[1], end_cell[1] + 1):
                for z in range(start_cell[2], end_cell[2] + 1):
                    if (x, y, z) in self.grid:
                        self.grid[(x, y, z)].discard((x_start, y_start, z_start, x_end, y_end, z_end))
                        if not self.grid[(x, y, z)]:
                            self.occupied_cells.discard((x, y, z))

    def get_occupied_regions(self):
        """Get all occupied regions in the grid"""
        regions = set()
        for cell in self.occupied_cells:
            regions.update(self.grid[cell])
        return regions

class SpaceOctree:
    def __init__(self, center: np.ndarray, size: float, max_depth: int = 4):
        self.root = OctreeNode(center, size, [])
        self.max_depth = max_depth
        self.item_nodes = {}
        self.spatial_hash = defaultdict(list)
        self.grid_size = size / 8
        # Add cache for bounds checks
        self._bounds_cache = {}

    def _get_cached_bounds(self, start: np.ndarray, end: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Cache bounds calculations for better performance"""
        key = (tuple(start), tuple(end))
        if key not in self._bounds_cache:
            self._bounds_cache[key] = (start, end)
        return self._bounds_cache[key]

    def subdivide(self, node: OctreeNode) -> None:
        half_size = node.size / 2
        offsets = [
            np.array([-1, -1, -1]), np.array([1, -1, -1]),
            np.array([-1, 1, -1]), np.array([1, 1, -1]),
            np.array([-1, -1, 1]), np.array([1, -1, 1]),
            np.array([-1, 1, 1]), np.array([1, 1, 1])
        ]
        
        for offset in offsets:
            child_center = node.center + (offset * half_size/2)
            child = OctreeNode(child_center, half_size, [], depth=node.depth + 1)
            node.children.append(child)

    def insert_item(self, itemId: Union[str, int], position: Dict, rotation: str, priority: int) -> bool:
        itemId_str = str(itemId)
        
        start = np.array([
            position["startCoordinates"]["width"],
            position["startCoordinates"]["depth"],
            position["startCoordinates"]["height"]
        ])
        end = np.array([
            position["endCoordinates"]["width"],
            position["endCoordinates"]["depth"],
            position["endCoordinates"]["height"]
        ])
        
        # Use cached bounds
        start, end = self._get_cached_bounds(start, end)
        
        # Try to find a suitable node without recursion first
        node = self._find_suitable_node(start, end)
        if node:
            node.occupied = True
            node.itemId = itemId_str
            node.rotation = rotation
            node.priority = priority
            self.item_nodes[itemId_str] = node
            self._add_to_spatial_hash(itemId_str, start, end)
            return True
            
        # If no suitable node found, try recursive insertion
        success = self._insert_recursive(self.root, start, end, itemId_str, rotation, priority)
        if success:
            node = self._find_node(itemId_str)
            self.item_nodes[itemId_str] = node
            self._add_to_spatial_hash(itemId_str, start, end)
        return success

    def _find_suitable_node(self, start: np.ndarray, end: np.ndarray) -> Optional[OctreeNode]:
        """Non-recursive node finding with early termination"""
        queue = [self.root]
        while queue:
            node = queue.pop(0)
            if node.occupied:
                continue
                
            node_min = node.center - node.size/2
            node_max = node.center + node.size/2
            
            if not self._bounds_overlap(start, end, node_min, node_max):
                continue
                
            if self._bounds_similar(start, end, node_min, node_max):
                return node
                
            if node.children:
                queue.extend(node.children)
            elif node.depth < self.max_depth:
                self.subdivide(node)
                queue.extend(node.children)
                
        return None

    def _insert_recursive(self, node: OctreeNode, start: np.ndarray, end: np.ndarray, 
                         itemId: str, rotation: str, priority: int) -> bool:
        if node.occupied:
            return False

        node_min = node.center - node.size/2
        node_max = node.center + node.size/2

        if not self._bounds_overlap(start, end, node_min, node_max):
            return False

        if self._bounds_similar(start, end, node_min, node_max):
            node.occupied = True
            node.itemId = itemId
            node.rotation = rotation
            node.priority = priority
            return True

        if not node.children and node.depth < self.max_depth:
            self.subdivide(node)

        if node.children:
            for child in node.children:
                if self._insert_recursive(child, start, end, itemId, rotation, priority):
                    return True

        return False

    def _add_to_spatial_hash(self, itemId: str, start: np.ndarray, end: np.ndarray):
        """Add item to spatial hash for faster neighbor lookups"""
        # Calculate grid cells that this item occupies
        start_cell = (int(start[0] // self.grid_size), 
                     int(start[1] // self.grid_size), 
                     int(start[2] // self.grid_size))
        end_cell = (int(end[0] // self.grid_size) + 1, 
                   int(end[1] // self.grid_size) + 1, 
                   int(end[2] // self.grid_size) + 1)
        
        # Add item to all cells it intersects
        for x in range(start_cell[0], end_cell[0]):
            for y in range(start_cell[1], end_cell[1]):
                for z in range(start_cell[2], end_cell[2]):
                    self.spatial_hash[(x, y, z)].append(itemId)

    def _bounds_overlap(self, min1: np.ndarray, max1: np.ndarray, 
                       min2: np.ndarray, max2: np.ndarray) -> bool:
        return np.all(max1 >= min2) and np.all(max2 >= min1)

    def _bounds_similar(self, min1: np.ndarray, max1: np.ndarray, 
                       min2: np.ndarray, max2: np.ndarray, tolerance: float = 0.1) -> bool:
        size1 = max1 - min1
        size2 = max2 - min2
        return np.all(np.abs(size1 - size2) < tolerance)

    def _find_node(self, itemId: str) -> Optional[OctreeNode]:
        """Optimized node finding with early return"""
        def search(node: OctreeNode) -> Optional[OctreeNode]:
            if node.itemId == itemId:
                return node
            if not node.children:  # Early return if no children
                return None
            for child in node.children:
                result = search(child)
                if result:
                    return result
            return None
        return search(self.root)

    def get_item_neighbors(self, itemId: str) -> List[str]:
        """Get items adjacent to the given item using spatial hash for efficiency."""
        if itemId not in self.item_nodes:
            return []
        
        # Use spatial hash for faster neighbor finding
        neighbors = set()
        
        # Get the item's bounds
        node = self.item_nodes[itemId]
        half_size = node.size / 2
        start = node.center - half_size
        end = node.center + half_size
        
        # Calculate grid cells this item occupies
        start_cell = (int(start[0] // self.grid_size), 
                     int(start[1] // self.grid_size), 
                     int(start[2] // self.grid_size))
        end_cell = (int(end[0] // self.grid_size) + 1, 
                   int(end[1] // self.grid_size) + 1, 
                   int(end[2] // self.grid_size) + 1)
        
        # Get all items in those cells and adjacent cells
        for x in range(start_cell[0] - 1, end_cell[0] + 1):
            for y in range(start_cell[1] - 1, end_cell[1] + 1):
                for z in range(start_cell[2] - 1, end_cell[2] + 1):
                    for potential_neighbor in self.spatial_hash.get((x, y, z), []):
                        if potential_neighbor != itemId:
                            neighbors.add(potential_neighbor)
        
        return list(neighbors)

class AdvancedCargoPlacement:
    # Class-level storage for container states
    _container_states = {}

    def __init__(self, container_dims: Dict[str, float]):
        # Convert dimensions to integers
        self.width = int(container_dims["width"])
        self.depth = int(container_dims["depth"])
        self.height = int(container_dims["height"])
        
        # Create a unique key for this container
        self.container_key = f"{self.width}x{self.depth}x{self.height}"
        
        # Initialize or retrieve existing state
        if self.container_key not in self._container_states:
            self._container_states[self.container_key] = {
                'space_matrix': SparseMatrix(self.width, self.depth, self.height),
                'current_placements': {},
                'rearrangement_history': []
            }
        
        # Use the shared state
        self.space_matrix = self._container_states[self.container_key]['space_matrix']
        self.current_placements = self._container_states[self.container_key]['current_placements']
        self.rearrangement_history = self._container_states[self.container_key]['rearrangement_history']
        
        # Initialize without CSV loading
        self.items_dict = {}
        self._item_cache = {}
        self._dupe_cache = {}
        self.rotation_cache = {}

    def _get_cached_item(self, itemId: str) -> Optional[Dict]:
        """Get cached item data with memoization"""
        if itemId not in self._item_cache:
            if itemId in self.items_dict:
                self._item_cache[itemId] = self.items_dict[itemId]
            elif itemId in self._dupe_cache:
                self._item_cache[itemId] = self._dupe_cache[itemId]
            else:
                return None
        return self._item_cache[itemId]

    def calculate_accessibility_score(self, pos: Position3D, item: ItemDimensions) -> float:
        """Optimized accessibility score calculation"""
        try:
            # Convert itemId to string for consistency
            itemId_str = str(item.itemId)
            
            # 1. Priority Score (40%)
            priority_score = item.priority / 100
            
            # 2. Mass Score (30%) - heavier items should be placed lower
            mass_score = max(0.1, min(1.0, 1 - (item.mass / 1000)))  # Assuming max mass of 1000kg
            
            # 3. Blockage Score (30%) - simplify calculation
            blockage_score = 0.9  # Default
            
            # Calculate weighted score
            final_score = (
                0.4 * priority_score +
                0.3 * mass_score +
                0.3 * blockage_score
            )
            
            return round(final_score, 2)
        except Exception as e:
            print(f"Error calculating accessibility score: {str(e)}")
            return 0.5  # Default score to avoid failures

    def _is_blocking(self, neighbor_id: str, target_pos: Position3D) -> bool:
        """Simplified blocking check"""
        neighbor_node = self.octree.item_nodes.get(neighbor_id)
        if not neighbor_node:
            return False
        
        # Simplified check: just compare centers
        neighbor_center = neighbor_node.center
        return (0 <= neighbor_center[0] <= target_pos.x and
                0 <= neighbor_center[1] <= target_pos.y and
                0 <= neighbor_center[2] <= target_pos.z)
    
    def _can_place_item(self, pos: Position3D, item: ItemDimensions) -> bool:
        """Check if an item can be placed at a given position using sparse matrix."""
        # Convert item dimensions to integers
        item_width = int(item.width)
        item_depth = int(item.depth)
        item_height = int(item.height)
        
        # Check boundaries
        if (pos.x + item_width > self.width or
            pos.y + item_depth > self.depth or
            pos.z + item_height > self.height):
            return False

        # Check if space is already occupied using sparse matrix
        return not self.space_matrix.is_occupied(
            pos.x, pos.y, pos.z,
            pos.x + item_width,
            pos.y + item_depth,
            pos.z + item_height
        )

    def _place_item(self, pos: Position3D, item: ItemDimensions) -> None:
        """Place an item using sparse matrix"""
        # Convert item dimensions to integers
        item_width = int(item.width)
        item_depth = int(item.depth)
        item_height = int(item.height)
        
        self.space_matrix.occupy(
            pos.x, pos.y, pos.z,
            pos.x + item_width,
            pos.y + item_depth,
            pos.z + item_height
        )

    def get_90degree_rotations(self, item: ItemDimensions) -> List[Tuple[ItemDimensions, Rotation]]:
        """Get all valid 90-degree rotations for an item"""
        rotations = []
        
        # Original orientation
        rotations.append((item, Rotation.NO_ROTATION))
        
        # Rotate around X axis (90°)
        if item.height <= self.depth and item.depth <= self.height:
            rotated = ItemDimensions(
                width=item.width,
                depth=item.height,
                height=item.depth,
                mass=item.mass,
                priority=item.priority,
                itemId=item.itemId
            )
            rotations.append((rotated, Rotation.ROTATE_X))
        
        # Rotate around Y axis (90°)
        if item.width <= self.height and item.height <= self.width:
            rotated = ItemDimensions(
                width=item.height,
                depth=item.depth,
                height=item.width,
                mass=item.mass,
                priority=item.priority,
                itemId=item.itemId
            )
            rotations.append((rotated, Rotation.ROTATE_Y))
        
        # Rotate around Z axis (90°)
        if item.width <= self.depth and item.depth <= self.width:
            rotated = ItemDimensions(
                width=item.depth,
                depth=item.width,
                height=item.height,
                mass=item.mass,
                priority=item.priority,
                itemId=item.itemId
            )
            rotations.append((rotated, Rotation.ROTATE_Z))
        
        return rotations

    def _calculate_rearrangement_cost(self, old_pos: Position3D, new_pos: Position3D, item: ItemDimensions) -> float:
        """Calculate the cost of moving an item from old position to new position"""
        # Distance cost (Euclidean distance)
        distance = np.sqrt(
            (new_pos.x - old_pos.x)**2 +
            (new_pos.y - old_pos.y)**2 +
            (new_pos.z - old_pos.z)**2
        )
        
        # Priority cost (higher priority items are more expensive to move)
        priority_cost = item.priority / 100.0
        
        # Total cost is weighted combination
        return distance * (1 + priority_cost)

    def _find_rearrangement_path(self, item: ItemDimensions, target_pos: Position3D) -> List[Dict]:
        """Find the optimal path to rearrange items to make space for a new item"""
        # Get current position of the item
        current_pos = self.current_placements.get(str(item.itemId))
        if not current_pos:
            return []

        # Calculate potential moves
        moves = []
        temp_positions = []
        
        # Try to find a temporary position for the item
        temp_pos = self._find_temporary_position(item)
        if temp_pos:
            moves.append({
                'itemId': str(item.itemId),
                'from': {
                    'x': current_pos.x,
                    'y': current_pos.y,
                    'z': current_pos.z
                },
                'to': {
                    'x': temp_pos.x,
                    'y': temp_pos.y,
                    'z': temp_pos.z
                },
                'type': 'temporary'
            })
            temp_positions.append(temp_pos)
        
        # Move to final position
        moves.append({
            'itemId': str(item.itemId),
            'from': {
                'x': temp_pos.x if temp_pos else current_pos.x,
                'y': temp_pos.y if temp_pos else current_pos.y,
                'z': temp_pos.z if temp_pos else current_pos.z
            },
            'to': {
                'x': target_pos.x,
                'y': target_pos.y,
                'z': target_pos.z
            },
            'type': 'final'
        })
        
        return moves

    def _find_temporary_position(self, item: ItemDimensions) -> Optional[Position3D]:
        """Find a temporary position for an item during rearrangement"""
        # Try to find a position that doesn't require moving other items
        for x in range(0, self.width - int(item.width) + 1, 10):
            for y in range(0, self.depth - int(item.depth) + 1, 10):
                for z in range(0, self.height - int(item.height) + 1, 10):
                    pos = Position3D(x, y, z)
                    if self._can_place_item(pos, item):
                        return pos
        return None

    def rearrange_for_new_item(self, new_item: ItemDimensions) -> Tuple[List[Dict], bool]:
        """Attempt to rearrange existing items to make space for a new item"""
        rearrangements = []
        success = False
        
        # Get existing items with their priorities
        existing_items = []
        for itemId, pos in self.current_placements.items():
            # Get the item's dimensions and priority from the original data
            item_data = self.items_dict.get(itemId, {})
            if item_data:
                existing_items.append({
                    'itemId': itemId,
                    'position': pos,
                    'priority': item_data.get('priority', 0),
                    'width': item_data.get('width', 0),
                    'depth': item_data.get('depth', 0),
                    'height': item_data.get('height', 0)
                })
        
        # Sort existing items by priority (move less important items first)
        existing_items.sort(key=lambda x: x['priority'])
        
        # Try to find a position for the new item
        target_pos = self._find_best_position(new_item)
        if not target_pos:
            # If no direct position found, try rearranging
            for existing_item in existing_items:
                # Create ItemDimensions for the existing item
                item_dim = ItemDimensions(
                    width=existing_item['width'],
                    depth=existing_item['depth'],
                    height=existing_item['height'],
                    mass=existing_item['mass'],
                    priority=existing_item['priority'],
                    itemId=existing_item['itemId']
                )
                
                # Calculate potential moves
                moves = self._find_rearrangement_path(item_dim, target_pos)
                if moves:
                    rearrangements.extend(moves)
                    # Update current placements
                    for move in moves:
                        if move['type'] == 'final':
                            self.current_placements[move['itemId']] = Position3D(
                                move['to']['x'],
                                move['to']['y'],
                                move['to']['z']
                            )
                    success = True
                    break
        
        return rearrangements, success

    def find_optimal_placement(self, items: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Optimized placement algorithm with rearrangement support"""
        if not items:
            return [], []

        # Store all items in items_dict for later reference
        for item in items:
            itemId = str(item.get('itemId'))  # Ensure itemId is string
            self.items_dict[itemId] = {
                'width': item.get('width', 0),
                'depth': item.get('depth', 0),
                'height': item.get('height', 0),
                'mass': item.get('mass', 0),
                'priority': item.get('priority', 0),
                'itemId': itemId
            }

        # Sort items by priority and size for better placement
        sorted_items = sorted(items, 
                           key=lambda x: (-x.get('priority', 0), 
                                        -(x.get('width', 0) * 
                                          x.get('depth', 0) * 
                                          x.get('height', 0))))
        
        placements = []
        rearrangements = []
        
        # First, try to place all items without rearrangement
        for item in sorted_items:
            itemId = str(item.get('itemId'))  # Ensure itemId is string
            # Create ItemDimensions from input data
            item_dim = ItemDimensions(
                width=item.get('width', 0),
                depth=item.get('depth', 0),
                height=item.get('height', 0),
                mass=item.get('mass', 0),
                priority=item.get('priority', 0),
                itemId=itemId
            )
            
            # Try different rotations
            rotations = self.get_90degree_rotations(item_dim)
            placed = False
            
            for rotated_item, rotation in rotations:
                # Find best position for this rotation
                best_pos = self._find_best_position(rotated_item)
                if best_pos and self._can_place_item(best_pos, rotated_item):
                    # Place the item
                    self._place_item(best_pos, rotated_item)
                    self.current_placements[itemId] = best_pos
                    
                    placements.append({
                        'itemId': itemId,
                        'position': {
                            'startCoordinates': {
                                'width': float(best_pos.x),
                                'depth': float(best_pos.y),
                                'height': float(best_pos.z)
                            },
                            'endCoordinates': {
                                'width': float(best_pos.x + rotated_item.width),
                                'depth': float(best_pos.y + rotated_item.depth),
                                'height': float(best_pos.z + rotated_item.height)
                            }
                        },
                        'rotation': rotation.value
                    })
                    placed = True
                    break
        
        # Now try to place any remaining items with rearrangement
        for item in sorted_items:
            itemId = str(item.get('itemId'))
            if itemId in [p['itemId'] for p in placements]:
                continue
                
            item_dim = ItemDimensions(
                width=item.get('width', 0),
                depth=item.get('depth', 0),
                height=item.get('height', 0),
                mass=item.get('mass', 0),
                priority=item.get('priority', 0),
                itemId=itemId
            )
            
            # Try different rotations
            rotations = self.get_90degree_rotations(item_dim)
            placed = False
            
            for rotated_item, rotation in rotations:
                # Find best position for this rotation
                best_pos = self._find_best_position(rotated_item)
                if best_pos:
                    # Check if rearrangement is needed
                    if not self._can_place_item(best_pos, rotated_item):
                        # Try to rearrange existing items
                        item_rearrangements, success = self.rearrange_for_new_item(rotated_item)
                        if success:
                            rearrangements.extend(item_rearrangements)
                            # Update the space matrix after rearrangement
                            for move in item_rearrangements:
                                if move['type'] == 'final':
                                    # Clear old position
                                    old_pos = Position3D(
                                        move['from']['x'],
                                        move['from']['y'],
                                        move['from']['z']
                                    )
                                    self.space_matrix.clear(
                                        old_pos.x, old_pos.y, old_pos.z,
                                        old_pos.x + int(rotated_item.width),
                                        old_pos.y + int(rotated_item.depth),
                                        old_pos.z + int(rotated_item.height)
                                    )
                                    # Mark new position
                                    new_pos = Position3D(
                                        move['to']['x'],
                                        move['to']['y'],
                                        move['to']['z']
                                    )
                                    self.space_matrix.occupy(
                                        new_pos.x, new_pos.y, new_pos.z,
                                        new_pos.x + int(rotated_item.width),
                                        new_pos.y + int(rotated_item.depth),
                                        new_pos.z + int(rotated_item.height)
                                    )
                    
                    # Place the item
                    self._place_item(best_pos, rotated_item)
                    self.current_placements[itemId] = best_pos
                    
                    placements.append({
                        'itemId': itemId,
                        'position': {
                            'startCoordinates': {
                                'width': float(best_pos.x),
                                'depth': float(best_pos.y),
                                'height': float(best_pos.z)
                            },
                            'endCoordinates': {
                                'width': float(best_pos.x + rotated_item.width),
                                'depth': float(best_pos.y + rotated_item.depth),
                                'height': float(best_pos.z + rotated_item.height)
                            }
                        },
                        'rotation': rotation.value
                    })
                    placed = True
                    break
                
        return placements, rearrangements

    def _find_best_position(self, item: ItemDimensions) -> Optional[Position3D]:
        """Optimized position finding with spatial partitioning"""
        # Use grid-based search
        grid_size = 10
        # Convert item dimensions to integers
        item_width = int(item.width)
        item_depth = int(item.depth)
        item_height = int(item.height)
        
        # First try to find a position that doesn't require rearrangement
        for x in range(0, self.width - item_width + 1, grid_size):
            for y in range(0, self.depth - item_depth + 1, grid_size):
                for z in range(0, self.height - item_height + 1, grid_size):
                    pos = Position3D(x, y, z)
                    if self._can_place_item(pos, item):
                        return pos
        
        # If no direct position found, try to find a position that requires minimal rearrangement
        best_pos = None
        min_rearrangement_cost = float('inf')
        
        for x in range(0, self.width - item_width + 1, grid_size):
            for y in range(0, self.depth - item_depth + 1, grid_size):
                for z in range(0, self.height - item_height + 1, grid_size):
                    pos = Position3D(x, y, z)
                    # Check if this position overlaps with any existing items
                    if self.space_matrix.is_occupied(x, y, z, x + item_width, y + item_depth, z + item_height):
                        # Calculate rearrangement cost for this position
                        cost = self._calculate_rearrangement_cost_for_position(pos, item)
                        if cost < min_rearrangement_cost:
                            min_rearrangement_cost = cost
                            best_pos = pos
        
        return best_pos

    def _calculate_rearrangement_cost_for_position(self, pos: Position3D, item: ItemDimensions) -> float:
        """Calculate the cost of rearranging items to make space for a new item at the given position"""
        total_cost = 0.0
        item_width = int(item.width)
        item_depth = int(item.depth)
        item_height = int(item.height)
        
        # Get all occupied regions that overlap with the target position
        for region in self.space_matrix.get_occupied_regions():
            x_start, y_start, z_start, x_end, y_end, z_end = region
            if (pos.x < x_end and pos.x + item_width > x_start and
                pos.y < y_end and pos.y + item_depth > y_start and
                pos.z < z_end and pos.z + item_height > z_start):
                # Calculate cost to move this item
                old_pos = Position3D(x_start, y_start, z_start)
                # Find a temporary position
                temp_pos = self._find_temporary_position(item)
                if temp_pos:
                    cost = self._calculate_rearrangement_cost(old_pos, temp_pos, item)
                    total_cost += cost
        
        return total_cost