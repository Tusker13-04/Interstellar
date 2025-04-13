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
        # Convert dimensions to integers and store as floats for precise calculations
        self.width = float(container_dims["width"])
        self.depth = float(container_dims["depth"])
        self.height = float(container_dims["height"])
        
        # Create a unique key for this container
        self.container_key = f"{self.width}x{self.depth}x{self.height}"
        
        # Initialize or retrieve existing state
        if self.container_key not in self._container_states:
            self._container_states[self.container_key] = {
                'space_matrix': SparseMatrix(int(self.width), int(self.depth), int(self.height)),
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

        # Add epsilon for floating point comparisons
        self.EPSILON = 1e-6

    def _validate_coordinates(self, start_coords: Dict[str, float], end_coords: Dict[str, float]) -> bool:
        """Validate if coordinates are within container bounds and properly ordered"""
        # Check if coordinates are within container bounds
        if (start_coords['width'] < 0 or start_coords['width'] > self.width or
            start_coords['depth'] < 0 or start_coords['depth'] > self.depth or
            start_coords['height'] < 0 or start_coords['height'] > self.height or
            end_coords['width'] < 0 or end_coords['width'] > self.width or
            end_coords['depth'] < 0 or end_coords['depth'] > self.depth or
            end_coords['height'] < 0 or end_coords['height'] > self.height):
            return False
            
        # Check if end coordinates are greater than start coordinates
        if (end_coords['width'] <= start_coords['width'] or
            end_coords['depth'] <= start_coords['depth'] or
            end_coords['height'] <= start_coords['height']):
            return False
            
        return True

    def _check_overlap(self, item1_start: Dict[str, float], item1_end: Dict[str, float],
                      item2_start: Dict[str, float], item2_end: Dict[str, float]) -> bool:
        """Check if two items overlap"""
        return not (
            item1_end['width'] <= item2_start['width'] + self.EPSILON or
            item1_start['width'] >= item2_end['width'] - self.EPSILON or
            item1_end['depth'] <= item2_start['depth'] + self.EPSILON or
            item1_start['depth'] >= item2_end['depth'] - self.EPSILON or
            item1_end['height'] <= item2_start['height'] + self.EPSILON or
            item1_start['height'] >= item2_end['height'] - self.EPSILON
        )

    def _find_best_position(self, item: ItemDimensions) -> Optional[Position3D]:
        """Find the best position for an item using a more precise algorithm"""
        best_pos = None
        best_score = float('-inf')
        
        # Convert dimensions to float for precise calculations
        item_width = float(item.width)
        item_depth = float(item.depth)
        item_height = float(item.height)
        
        # Get all existing placements
        occupied_spaces = []
        for placement in self.current_placements.values():
            occupied_spaces.append({
                'start': placement['startCoordinates'],
                'end': placement['endCoordinates']
            })
        
        # Create potential positions list
        potential_positions = [(0, 0, 0)]  # Start with bottom-left-front corner
        
        # Add positions next to existing items
        for space in occupied_spaces:
            # Add positions on top of items
            potential_positions.append((
                space['start']['width'],
                space['start']['depth'],
                space['end']['height']
            ))
            # Add positions next to items
            potential_positions.append((
                space['end']['width'],
                space['start']['depth'],
                space['start']['height']
            ))
            potential_positions.append((
                space['start']['width'],
                space['end']['depth'],
                space['start']['height']
            ))
        
        # Filter and sort potential positions
        potential_positions = list(set(potential_positions))  # Remove duplicates
        potential_positions.sort(key=lambda p: (p[2], p[1], p[0]))  # Sort by height, depth, width
        
        for x, y, z in potential_positions:
            # Skip if position would place item outside container
            if (x + item_width > self.width + self.EPSILON or
                y + item_depth > self.depth + self.EPSILON or
                z + item_height > self.height + self.EPSILON):
                continue
                
            pos = Position3D(x, y, z)
            
            # Check if position is valid (no overlaps)
            valid = True
            new_item_start = {
                'width': x, 'depth': y, 'height': z
            }
            new_item_end = {
                'width': x + item_width,
                'depth': y + item_depth,
                'height': z + item_height
            }
            
            for space in occupied_spaces:
                if self._check_overlap(new_item_start, new_item_end,
                                    space['start'], space['end']):
                    valid = False
                    break
            
            if valid:
                # Calculate accessibility score
                score = self.calculate_accessibility_score(pos, item)
                if score > best_score:
                    best_score = score
                    best_pos = pos
        
        return best_pos

    def find_optimal_placement(self, items: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Optimized placement algorithm with improved coordinate handling"""
        if not items:
            return [], []

        # Store all items in items_dict for later reference
        for item in items:
            itemId = str(item.get('itemId'))
            self.items_dict[itemId] = {
                'width': float(item.get('width', 0)),
                'depth': float(item.get('depth', 0)),
                'height': float(item.get('height', 0)),
                'mass': float(item.get('mass', 0)),
                'priority': float(item.get('priority', 0)),
                'itemId': itemId
            }

        # Sort items by priority and volume
        sorted_items = sorted(items, 
                           key=lambda x: (-x.get('priority', 0), 
                                        -(float(x.get('width', 0)) * 
                                          float(x.get('depth', 0)) * 
                                          float(x.get('height', 0)))))
        
        placements = []
        rearrangements = []
        
        for item in sorted_items:
            itemId = str(item.get('itemId'))
            item_dim = ItemDimensions(
                width=float(item.get('width', 0)),
                depth=float(item.get('depth', 0)),
                height=float(item.get('height', 0)),
                mass=float(item.get('mass', 0)),
                priority=float(item.get('priority', 0)),
                itemId=itemId
            )
            
            # Try different rotations
            rotations = self.get_90degree_rotations(item_dim)
            placed = False
            
            for rotated_item, rotation in rotations:
                best_pos = self._find_best_position(rotated_item)
                if best_pos:
                    # Validate coordinates
                    start_coords = {
                        'width': float(best_pos.x),
                        'depth': float(best_pos.y),
                        'height': float(best_pos.z)
                    }
                    end_coords = {
                        'width': float(best_pos.x + rotated_item.width),
                        'depth': float(best_pos.y + rotated_item.depth),
                        'height': float(best_pos.z + rotated_item.height)
                    }
                    
                    if self._validate_coordinates(start_coords, end_coords):
                        # Update current placements with precise coordinates
                        self.current_placements[itemId] = {
                            'startCoordinates': start_coords,
                            'endCoordinates': end_coords
                        }
                        
                        placements.append({
                            'itemId': itemId,
                            'position': {
                                'startCoordinates': start_coords,
                                'endCoordinates': end_coords
                            },
                            'rotation': rotation.value
                        })
                        placed = True
                        break
            
            if not placed:
                print(f"Warning: Could not place item {itemId}")
        
        return placements, rearrangements

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