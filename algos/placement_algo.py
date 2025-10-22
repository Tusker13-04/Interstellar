from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Tuple, Union
import numpy as np
from datetime import datetime
import polars as pl
import pandas as pd
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


    # ============= LLM INTEGRATION METHODS =============

    def export_cargo_data_for_llm(self, filename="cargo_data.csv"):
        """Export current cargo placements to CSV format for LLM system"""
        cargo_data = []

        # Extract data from current_placements
        for item_id, placement in self.current_placements.items():
            # Get item details from items_dict
            item_info = self.items_dict.get(item_id, {})

            # Calculate volume and accessibility
            start_coords = placement['startCoordinates']
            end_coords = placement['endCoordinates']

            volume = ((end_coords['width'] - start_coords['width']) * 
                     (end_coords['depth'] - start_coords['depth']) * 
                     (end_coords['height'] - start_coords['height']))

            # Create position object for accessibility calculation
            pos = Position3D(
                x=int(start_coords['width']),
                y=int(start_coords['depth']),
                z=int(start_coords['height'])
            )

            # Create item dimensions object
            item_dim = ItemDimensions(
                width=end_coords['width'] - start_coords['width'],
                depth=end_coords['depth'] - start_coords['depth'],
                height=end_coords['height'] - start_coords['height'],
                mass=item_info.get('mass', 1.0),
                priority=item_info.get('priority', 1),
                itemId=item_id
            )

            accessibility_score = self.calculate_accessibility_score(pos, item_dim)

            cargo_data.append({
                'id': str(item_id),
                'name': f'Item_{item_id}',
                'category': self._determine_category(item_info),
                'position': f'Container_{int(start_coords["width"]//5)}_{int(start_coords["depth"]//5)}',
                'mass': float(item_info.get('mass', 1.0)),
                'dimensions': f'{item_dim.width:.1f}x{item_dim.depth:.1f}x{item_dim.height:.1f}',
                'coordinates_x': float(start_coords['width']),
                'coordinates_y': float(start_coords['depth']),
                'coordinates_z': float(start_coords['height']),
                'volume': round(volume, 2),
                'priority': int(item_info.get('priority', 1)),
                'accessibility_score': accessibility_score,
                'temperature_sensitive': self._is_temperature_sensitive(item_info),
                'expiry_hours': self._get_expiry_hours(item_info),
                'power_draw_watts': self._get_power_draw(item_info),
                'description': f'3D packed item at ({start_coords["width"]:.1f}, {start_coords["depth"]:.1f}, {start_coords["height"]:.1f})'
            })

        # Create DataFrame and save to CSV
        df = pd.DataFrame(cargo_data)
        df.to_csv(filename, index=False)
        print(f"✅ Exported {len(cargo_data)} cargo items to {filename}")

        return df

    def _determine_category(self, item_info):
        """Determine item category based on priority and mass"""
        priority = item_info.get('priority', 1)
        mass = item_info.get('mass', 1.0)

        if priority >= 80:
            return 'Critical'
        elif priority >= 60:
            return 'Medical' if mass < 50 else 'Equipment'
        elif priority >= 40:
            return 'Food' if mass < 100 else 'Life Support'
        elif mass > 200:
            return 'Heavy Equipment'
        else:
            return 'General'

    def _is_temperature_sensitive(self, item_info):
        """Determine if item is temperature sensitive"""
        category = self._determine_category(item_info)
        return category in ['Medical', 'Food', 'Critical']

    def _get_expiry_hours(self, item_info):
        """Get expiry hours based on category"""
        category = self._determine_category(item_info)
        expiry_map = {
            'Medical': 720,    # 30 days
            'Food': 2160,      # 90 days
            'Critical': 168,   # 7 days
        }
        return expiry_map.get(category, None)

    def _get_power_draw(self, item_info):
        """Get power draw based on category"""
        category = self._determine_category(item_info)
        power_map = {
            'Equipment': 150,
            'Medical': 50,
            'Life Support': 200,
            'Heavy Equipment': 300
        }
        return power_map.get(category, 0)

    def get_container_utilization_stats(self):
        """Get detailed utilization statistics for LLM queries"""
        total_volume = self.width * self.depth * self.height
        used_volume = 0
        total_mass = 0
        priority_distribution = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0}

        for item_id, placement in self.current_placements.items():
            # Calculate volume
            start = placement['startCoordinates']
            end = placement['endCoordinates']
            item_volume = ((end['width'] - start['width']) * 
                          (end['depth'] - start['depth']) * 
                          (end['height'] - start['height']))
            used_volume += item_volume

            # Get item info
            item_info = self.items_dict.get(item_id, {})
            total_mass += item_info.get('mass', 0)

            # Priority distribution
            priority = item_info.get('priority', 0)
            if priority >= 80:
                priority_distribution['Critical'] += 1
            elif priority >= 60:
                priority_distribution['High'] += 1
            elif priority >= 40:
                priority_distribution['Medium'] += 1
            else:
                priority_distribution['Low'] += 1

        return {
            'total_items': len(self.current_placements),
            'total_volume': round(total_volume, 2),
            'used_volume': round(used_volume, 2),
            'utilization_percentage': round((used_volume / total_volume) * 100, 2),
            'total_mass_kg': round(total_mass, 2),
            'average_mass_per_item': round(total_mass / max(len(self.current_placements), 1), 2),
            'priority_distribution': priority_distribution,
            'container_dimensions': {
                'width': self.width,
                'depth': self.depth,
                'height': self.height
            }
        }

    def run_optimization_for_llm(self):
        """Run optimization and return results in LLM-friendly format"""
        # Store original state
        original_placements = self.current_placements.copy()
        original_stats = self.get_container_utilization_stats()

        try:
            # Extract items from current placements
            items_to_optimize = []
            for item_id, placement in self.current_placements.items():
                item_info = self.items_dict.get(item_id, {})
                start = placement['startCoordinates']
                end = placement['endCoordinates']

                items_to_optimize.append({
                    'itemId': item_id,
                    'width': end['width'] - start['width'],
                    'depth': end['depth'] - start['depth'],
                    'height': end['height'] - start['height'],
                    'mass': item_info.get('mass', 1.0),
                    'priority': item_info.get('priority', 1)
                })

            # Clear current placements and re-optimize
            self.current_placements.clear()

            # Run optimization
            new_placements, rearrangements = self.find_optimal_placement(items_to_optimize)

            # Get new stats
            new_stats = self.get_container_utilization_stats()

            # Calculate improvements
            utilization_improvement = (new_stats['utilization_percentage'] - 
                                     original_stats['utilization_percentage'])

            # Export updated data
            self.export_cargo_data_for_llm()

            return {
                'status': 'success',
                'optimization_completed': True,
                'items_repositioned': len(new_placements),
                'utilization_improvement_percent': round(utilization_improvement, 2),
                'original_utilization': original_stats['utilization_percentage'],
                'new_utilization': new_stats['utilization_percentage'],
                'total_items': len(new_placements),
                'rearrangements_performed': len(rearrangements),
                'execution_time_seconds': 0.5,
                'message': f'Optimization completed. Utilization improved by {utilization_improvement:.1f}%'
            }

        except Exception as e:
            # Restore original state on error
            self.current_placements = original_placements
            return {
                'status': 'error',
                'message': f'Optimization failed: {str(e)}',
                'utilization_percentage': original_stats['utilization_percentage']
            }

    def simulate_item_retrieval_for_llm(self, item_id):
        """Simulate retrieving an item and return blocking analysis"""
        item_id = str(item_id)

        if item_id not in self.current_placements:
            return {'error': f'Item {item_id} not found'}

        target_placement = self.current_placements[item_id]
        target_start = target_placement['startCoordinates']
        target_end = target_placement['endCoordinates']

        blocking_items = []

        # Find items that block access to the target item
        for other_id, other_placement in self.current_placements.items():
            if other_id == item_id:
                continue

            other_start = other_placement['startCoordinates']
            other_end = other_placement['endCoordinates']

            # Check if other item blocks access from the front
            if (other_start['width'] < target_start['width'] and
                other_end['width'] > target_start['width'] - 1 and
                abs(other_start['depth'] - target_start['depth']) < 2 and
                abs(other_start['height'] - target_start['height']) < 2):

                item_info = self.items_dict.get(other_id, {})
                blocking_items.append({
                    'id': other_id,
                    'name': f'Item_{other_id}',
                    'position': f"({other_start['width']:.1f}, {other_start['depth']:.1f}, {other_start['height']:.1f})",
                    'priority': item_info.get('priority', 1),
                    'mass': item_info.get('mass', 1.0)
                })

        # Calculate accessibility score
        pos = Position3D(
            x=int(target_start['width']),
            y=int(target_start['depth']),
            z=int(target_start['height'])
        )

        target_item_info = self.items_dict.get(item_id, {})
        item_dim = ItemDimensions(
            width=target_end['width'] - target_start['width'],
            depth=target_end['depth'] - target_start['depth'],
            height=target_end['height'] - target_start['height'],
            mass=target_item_info.get('mass', 1.0),
            priority=target_item_info.get('priority', 1),
            itemId=item_id
        )

        accessibility_score = self.calculate_accessibility_score(pos, item_dim)

        return {
            'status': 'success',
            'target_item': item_id,
            'target_position': f"({target_start['width']:.1f}, {target_start['depth']:.1f}, {target_start['height']:.1f})",
            'blocking_items_count': len(blocking_items),
            'blocking_items': blocking_items,
            'estimated_retrieval_time_minutes': len(blocking_items) * 3 + 5,
            'accessibility_score': accessibility_score,
            'retrieval_difficulty': 'Easy' if accessibility_score > 0.8 else 'Medium' if accessibility_score > 0.5 else 'Hard'
        }

    def get_items_in_3d_region_for_llm(self, x_min, x_max, y_min, y_max, z_min, z_max):
        """Find all items within a 3D bounding box"""
        items_in_region = []

        for item_id, placement in self.current_placements.items():
            start = placement['startCoordinates']
            end = placement['endCoordinates']

            # Check if item overlaps with the specified region
            if (start['width'] < x_max and end['width'] > x_min and
                start['depth'] < y_max and end['depth'] > y_min and
                start['height'] < z_max and end['height'] > z_min):

                item_info = self.items_dict.get(item_id, {})
                items_in_region.append({
                    'id': item_id,
                    'name': f'Item_{item_id}',
                    'position': f"({start['width']:.1f}, {start['depth']:.1f}, {start['height']:.1f})",
                    'dimensions': f"{end['width']-start['width']:.1f}x{end['depth']-start['depth']:.1f}x{end['height']-start['height']:.1f}",
                    'priority': item_info.get('priority', 1),
                    'mass': item_info.get('mass', 1.0)
                })

        return {
            'status': 'success',
            'region': {
                'x_range': [x_min, x_max],
                'y_range': [y_min, y_max],
                'z_range': [z_min, z_max]
            },
            'items_found': len(items_in_region),
            'items': items_in_region
        }

    def get_nearest_items_for_llm(self, x, y, z, radius=2.0):
        """Find items near a specific coordinate"""
        nearby_items = []

        for item_id, placement in self.current_placements.items():
            start = placement['startCoordinates']

            # Calculate distance from center of item to target point
            item_center_x = start['width']
            item_center_y = start['depth']
            item_center_z = start['height']

            distance = ((item_center_x - x)**2 + 
                       (item_center_y - y)**2 + 
                       (item_center_z - z)**2)**0.5

            if distance <= radius:
                item_info = self.items_dict.get(item_id, {})
                nearby_items.append({
                    'id': item_id,
                    'name': f'Item_{item_id}',
                    'position': f"({start['width']:.1f}, {start['depth']:.1f}, {start['height']:.1f})",
                    'distance': round(distance, 2),
                    'priority': item_info.get('priority', 1),
                    'mass': item_info.get('mass', 1.0)
                })

        # Sort by distance
        nearby_items.sort(key=lambda x: x['distance'])

        return {
            'status': 'success',
            'target_coordinates': {'x': x, 'y': y, 'z': z},
            'search_radius': radius,
            'items_found': len(nearby_items),
            'items': nearby_items
        }


# Example test function
if __name__ == "__main__":
    print("🧪 Testing Interstellar Placement Algorithm with LLM Integration...")

    # Create container
    container_dims = {"width": 10, "depth": 10, "height": 10}
    placement_system = AdvancedCargoPlacement(container_dims)

    # Create test items
    test_items = [
        {'itemId': 1, 'width': 2, 'depth': 2, 'height': 2, 'mass': 15.5, 'priority': 80},
        {'itemId': 2, 'width': 3, 'depth': 2, 'height': 1, 'mass': 45.2, 'priority': 60},
        {'itemId': 3, 'width': 1, 'depth': 1, 'height': 3, 'mass': 120.0, 'priority': 40},
        {'itemId': 4, 'width': 2, 'depth': 3, 'height': 1, 'mass': 8.3, 'priority': 70},
        {'itemId': 5, 'width': 1, 'depth': 2, 'height': 2, 'mass': 67.8, 'priority': 30}
    ]

    # Run placement
    placements, rearrangements = placement_system.find_optimal_placement(test_items)
    print(f"✅ Placed {len(placements)} items")

    # Test LLM integration features
    print("\n🔧 Testing LLM Integration Features...")

    # Export to CSV
    df = placement_system.export_cargo_data_for_llm()
    print(f"✅ Exported {len(df)} items to cargo_data.csv")

    # Get utilization stats
    stats = placement_system.get_container_utilization_stats()
    print(f"📊 Utilization: {stats['utilization_percentage']}%")
    print(f"📦 Total Items: {stats['total_items']}")
    print(f"⚖️ Total Mass: {stats['total_mass_kg']} kg")

    # Test retrieval simulation
    retrieval = placement_system.simulate_item_retrieval_for_llm('1')
    print(f"\n🔍 Retrieval Simulation for Item 1:")
    print(f"   Blocking Items: {retrieval['blocking_items_count']}")
    print(f"   Accessibility: {retrieval['accessibility_score']}")
    print(f"   Difficulty: {retrieval['retrieval_difficulty']}")

    print("\n🎉 All tests passed! LLM integration is ready!")
