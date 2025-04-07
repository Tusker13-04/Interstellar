from dataclasses import dataclass
from typing import List, Dict, Set, Tuple, Optional
from datetime import datetime
import numpy as np
import polars as pl
import heapq

@dataclass
class RetrievalNode:
    position: Tuple[int, int, int]
    g_cost: float  # Cost from start
    h_cost: float  # Heuristic cost to goal
    f_cost: float  # Total cost (g + h)
    parent: Optional['RetrievalNode'] = None
    priority_bonus: float = 0.0  # Priority-based bonus
    
    def __lt__(self, other):
        # For priority queue comparison
        return (self.f_cost - self.priority_bonus) < (other.f_cost - other.priority_bonus)

@dataclass
class RetrievalPath:
    steps: List[Dict]
    total_cost: float
    priority_score: float
    safety_score: float

class PriorityAStarRetrieval:
    def __init__(self, container_dims: dict):
        """Initialize with container dimensions"""
        # Convert dimensions to integers
        self.width = int(container_dims["width"])
        self.depth = int(container_dims["depth"])
        self.height = int(container_dims["height"])
        
        # Initialize occupied spaces set
        self.occupied_spaces = set()
        
        # Initialize priority queue for A* search
        self.priority_queue = []
        
        # Initialize visited nodes set
        self.visited = set()
        
        self.items_data = {}
        # Pre-compute direction vectors for neighbor calculation
        self.directions = [(0,0,1), (0,0,-1), (0,1,0), (0,-1,0), (1,0,0), (-1,0,0)]
        self.load_items_data()

    def load_items_data(self):
        """Load and cache items data from CSV using Polars for faster processing"""
        try:
            # Using Polars' lazy evaluation for better performance
            items_df = pl.scan_csv("imported_items.csv").collect()
            self.items_data = {
                str(row["itemId"]): row 
                for row in items_df.to_dicts()
            }
        except Exception as e:
            print(f"Error loading items data: {str(e)}")
            # Initialize with empty dict to prevent further errors
            self.items_data = {}

    def calculate_priority_score(self, itemId: str) -> float:
        """Calculate priority score based on multiple factors"""
        item = self.items_data.get(str(itemId), {})
        if not item:
            return 0.0

        # Base priority (0-1)
        priority_score = item.get("priority", 0) / 100

        # Expiry date factor
        expiry_score = 1.0
        if "expiryDate" in item and item["expiryDate"]:
            try:
                expiry = datetime.strptime(item["expiryDate"], "%d-%m-%y")
                days_until_expiry = (expiry - datetime.now()).days
                # Higher priority for items expiring sooner
                expiry_score = max(0.1, min(1.0, 1 - (days_until_expiry / 365)))
            except (ValueError, TypeError):
                # Handle invalid date formats gracefully
                pass

        # Usage limit factor
        usage_score = 0.5
        if "usageLimit" in item and item["usageLimit"] is not None:
            try:
                usage_score = max(0.1, min(1.0, float(item["usageLimit"]) / 10))
            except (ValueError, TypeError):
                # Handle invalid usage limit values
                pass

        # Combined weighted score
        return (
            0.4 * priority_score +
            0.4 * expiry_score +
            0.2 * usage_score
        )

    def manhattan_distance(self, pos1: Tuple[int, int, int], pos2: Tuple[int, int, int]) -> float:
        """Calculate Manhattan distance with priority weighting"""
        # ing direct array unpacking for better performance
        x1, y1, z1 = pos1
        x2, y2, z2 = pos2
        return abs(x1 - x2) + abs(y1 - y2) + abs(z1 - z2)

    def get_neighbors(self, pos: Tuple[int, int, int]) -> List[Tuple[int, int, int]]:
        """Get valid neighboring positions - optimized version"""
        x, y, z = pos
        # Pre-allocate for performance
        neighbors = []
        neighbors_append = neighbors.append  # Local function reference for speed
        
        for dx, dy, dz in self.directions:
            new_x, new_y, new_z = x + dx, y + dy, z + dz
            # Bounds checking first (faster than creating tuple then checking)
            if (0 <= new_x < self.width and 
                0 <= new_y < self.depth and 
                0 <= new_z < self.height):
                new_pos = (new_x, new_y, new_z)
                if new_pos not in self.occupied_spaces:
                    neighbors_append(new_pos)
                    
        return neighbors

    def is_valid_position(self, pos: Tuple[float, float, float]) -> bool:
        """Check if position is valid and unoccupied"""
        x, y, z = pos
        # Convert to integers for comparison with container dimensions
        x_int = int(x)
        y_int = int(y)
        z_int = int(z)
        
        # Check if the position is within container bounds - inclusive of boundaries
        if not (0 <= x_int <= self.width and
                0 <= y_int <= self.depth and
                0 <= z_int <= self.height):
            print(f"Position {pos} out of bounds - container dimensions: {self.width}x{self.depth}x{self.height}")
            return False
            
        # Check if the position is occupied
        # Convert to integer coordinates for occupied spaces check
        pos_int = (x_int, y_int, z_int)
        if pos_int in self.occupied_spaces:
            print(f"Position {pos} is occupied")
            return False
            
        return True

    def find_retrieval_path(self, start_pos: Tuple[float, float, float], 
                           target_pos: Tuple[float, float, float],
                           itemId: str) -> Optional[RetrievalPath]:
        """Find optimal retrieval path using A* with priority considerations"""
        print(f"\nFinding retrieval path from {start_pos} to {target_pos} for item {itemId}")
        
        # Convert positions to integers for path finding
        start_pos_int = (int(start_pos[0]), int(start_pos[1]), int(start_pos[2]))
        target_pos_int = (int(target_pos[0]), int(target_pos[1]), int(target_pos[2]))
        
        print(f"Container dimensions: {self.width}x{self.depth}x{self.height}")
        print(f"Converted positions - start: {start_pos_int}, target: {target_pos_int}")
        
        # Validate positions
        if not self.is_valid_position(start_pos):
            print(f"Invalid start position: {start_pos}")
            # Special case: start position is (0,0,0) - we should allow this as entry point
            if start_pos == (0, 0, 0):
                print("Allowing (0,0,0) as valid start position despite validation failure")
                # Make sure it's not in occupied spaces
                self.occupied_spaces.discard(start_pos_int)
            else:
                return None
                
        if not self.is_valid_position(target_pos):
            print(f"Invalid target position: {target_pos}")
            # Special exception for target position - we need to retrieve an item
            # even if its coordinates are outside the standard bounds
            if (0 <= target_pos_int[0] <= self.width + 5 and
                0 <= target_pos_int[1] <= self.depth + 5 and
                0 <= target_pos_int[2] <= self.height + 5):
                print(f"Target position slightly out of bounds but within tolerance - proceeding")
            else:
                return None

        # Using priority queue instead of set + min search
        open_pq = []
        open_set = set([start_pos_int])
        closed_set = set()
        
        # Priority bonus for the target item
        priority_bonus = self.calculate_priority_score(itemId)
        
        h_cost = self.manhattan_distance(start_pos_int, target_pos_int)
        start_node = RetrievalNode(
            position=start_pos_int,
            g_cost=0,
            h_cost=h_cost,
            f_cost=h_cost,  # f_cost = g_cost + h_cost
            priority_bonus=priority_bonus
        )
        
        # Using dictionary for O(1) node lookups
        nodes = {start_pos_int: start_node}
        
        # Add start node to priority queue
        heapq.heappush(open_pq, start_node)
        
        while open_pq:
            current = heapq.heappop(open_pq)
            current_pos = current.position
            
            # Node may have been updated with a better path after being added to queue
            if current.f_cost - current.priority_bonus > nodes[current_pos].f_cost - nodes[current_pos].priority_bonus:
                continue
                
            if current_pos == target_pos_int:
                print(f"Path found with {current.g_cost} steps")
                return self.reconstruct_path(current, itemId)
            
            # Safely remove from open_set if it exists
            if current_pos in open_set:
                open_set.remove(current_pos)
            closed_set.add(current_pos)
            
            for neighbor_pos in self.get_neighbors(current_pos):
                if neighbor_pos in closed_set:
                    continue
                
                g_cost = current.g_cost + 1  # Assuming uniform cost for movement
                
                if neighbor_pos not in open_set:
                    h_cost = self.manhattan_distance(neighbor_pos, target_pos_int)
                    f_cost = g_cost + h_cost
                    
                    neighbor = RetrievalNode(
                        position=neighbor_pos,
                        g_cost=g_cost,
                        h_cost=h_cost,
                        f_cost=f_cost,  # Explicitly calculate f_cost
                        priority_bonus=priority_bonus,
                        parent=current
                    )
                    
                    nodes[neighbor_pos] = neighbor
                    open_set.add(neighbor_pos)
                    heapq.heappush(open_pq, neighbor)
                    
                elif g_cost < nodes[neighbor_pos].g_cost:
                    # Better path found, update node
                    neighbor = nodes[neighbor_pos]
                    neighbor.g_cost = g_cost
                    neighbor.f_cost = g_cost + neighbor.h_cost
                    neighbor.parent = current
                    
                    # Re-add to priority queue with updated priority
                    heapq.heappush(open_pq, neighbor)
        
        print(f"No path found from {start_pos} to {target_pos}")
        return None  # No path found

    def reconstruct_path(self, final_node: RetrievalNode, itemId: str) -> RetrievalPath:
        """Reconstruct the retrieval path with steps"""
        path = []
        current = final_node
        
        while current.parent:
            path.append({
                "from": current.parent.position,
                "to": current.position,
                "itemId": itemId,
                "priority": self.calculate_priority_score(itemId)
            })
            current = current.parent
        
        path.reverse()
        
        # Calculate safety score based on path characteristics
        # For example, paths with fewer vertical movements might be safer
        vertical_movements = sum(1 for step in path 
                               if step["from"][2] != step["to"][2])
        path_length = len(path)
        safety_score = 1.0 if path_length == 0 else 1.0 - (vertical_movements / (path_length * 2))
        
        return RetrievalPath(
            steps=path,
            total_cost=final_node.g_cost,
            priority_score=final_node.priority_bonus,
            safety_score=max(0.1, min(1.0, safety_score))  # Ensure within 0.1-1.0 range
        )
    
    # API endpoint handler method
    def handle_retrieve_request(self, request_data: Dict) -> Dict:
        """Handle API endpoint requests to /api/retrieve"""
        try:
            # Extract required parameters from request
            start_position = tuple(request_data.get("startPosition", (0, 0, 0)))
            target_position = tuple(request_data.get("targetPosition"))
            itemId = request_data.get("itemId")
            
            # Update occupied spaces if provided
            if "occupiedSpaces" in request_data:
                self.occupied_spaces = set(tuple(pos) for pos in request_data["occupiedSpaces"])
            
            # Find retrieval path
            path = self.find_retrieval_path(start_position, target_position, itemId)
            
            if path:
                return {
                    "success": True,
                    "path": {
                        "steps": path.steps,
                        "totalCost": path.total_cost,
                        "priorityScore": path.priority_score,
                        "safetyScore": path.safety_score
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "No valid path found"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }