from typing import Dict, List, Union, Optional, Tuple, Any
from dataclasses import dataclass
import re
from collections import defaultdict

@dataclass
class Coordinates:
    width: float
    depth: float
    height: float

@dataclass
class Position:
    startCoordinates: Coordinates
    endCoordinates: Coordinates

class ItemSearchSystem:
    def __init__(self, items_data: List[dict], containers_data: List[dict], cargo_data: List[dict]):
        """Initialize with data from API endpoint"""
        # Process items data
        self.items_data = {}
        for item in items_data:
            itemId = str(item.get("itemId", ""))
            if itemId:
                self.items_data[itemId] = {
                    "name": item.get("name", ""),
                    "width": float(item.get("width", 0)),
                    "depth": float(item.get("depth", 0)),
                    "height": float(item.get("height", 0)),
                    "priority": int(item.get("priority", 1)),
                    "usageLimit": int(item.get("usageLimit", 0))
                }
        
        # Process containers data
        self.containers = {}
        for cont in containers_data:
            containerId = str(cont.get("containerId", ""))
            if containerId:
                self.containers[containerId] = {
                    "containerId": containerId,
                    "zone": cont.get("zone", ""),
                    "width": float(cont.get("width", 0)),
                    "depth": float(cont.get("depth", 0)),
                    "height": float(cont.get("height", 0))
                }

        # Process cargo data with positions
        self.cargo_data = {}
        for item in cargo_data:
            itemId = str(item.get("itemId", ""))
            if not itemId:
                continue
                
            coords_str = item.get("coordinates", "")
            if not coords_str:
                continue
                
            # Extract coordinates using regex
            coords = re.findall(r'[-+]?\d*\.\d+|[-+]?\d+', coords_str)
            if len(coords) >= 6:
                try:
                    self.cargo_data[itemId] = {
                        "zone": item.get("zone", ""),
                        "containerId": item.get("containerId", ""),
                        "position": {
                            "startCoordinates": {
                                "width": float(coords[0]),
                                "depth": float(coords[1]),
                                "height": float(coords[2])
                            },
                            "endCoordinates": {
                                "width": float(coords[3]),
                                "depth": float(coords[4]),
                                "height": float(coords[5])
                            }
                        }
                    }
                except (ValueError, IndexError) as e:
                    print(f"Error processing coordinates for item {itemId}: {e}")

    def search_by_id(self, itemId: Union[int, str]) -> dict:
        """Search for item by ID and calculate optimal retrieval steps"""
        itemId = str(itemId)
        
        if itemId not in self.items_data:
            return {
                "success": True,
                "found": False,
                "message": f"Item {itemId} not found in inventory"
            }
            
        if itemId not in self.cargo_data:
            return {
                "success": True,
                "found": False,
                "message": f"Item {itemId} exists but not placed in any container"
            }

        item_data = self.items_data[itemId]
        cargo_info = self.cargo_data[itemId]
        zone = cargo_info["zone"]
        
        # Find container for zone
        containerId = next(
            (cid for cid, cont in self.containers.items() if cont["zone"] == zone),
            None
        )
        
        if not containerId:
            return {
                "success": False,
                "found": False,
                "message": f"No container found for zone {zone}"
            }

        # Calculate retrieval steps
        retrieval_steps = self._calculate_retrieval_steps(itemId, zone)

        return {
            "success": True,
            "found": True,
            "item": {
                "itemId": int(itemId),
                "name": item_data["name"],
                "containerId": containerId,
                "zone": zone,
                "position": cargo_info["position"]
            },
            "retrieval_steps": retrieval_steps
        }

    def search_by_name(self, item_name: str) -> dict:
        """Search for item by name"""
        for itemId, data in self.items_data.items():
            if data["name"].lower() == item_name.lower():
                return self.search_by_id(itemId)
                
        return {
            "success": True,
            "found": False,
            "message": f"Item with name '{item_name}' not found"
        }

    def _calculate_retrieval_steps(self, target_itemId: str, zone: str) -> List[dict]:
        """Calculate optimal retrieval steps for an item using a dependency graph approach"""
        target_itemId = str(target_itemId)
        target_item = self.cargo_data[target_itemId]
        target_container = target_item["containerId"]
        target_start = target_item["position"]["startCoordinates"]
        target_end = target_item["position"]["endCoordinates"]
        target_priority = self.items_data[target_itemId]["priority"]
        
        # Find all items in the same container
        items_in_container = {
            str(itemId): data for itemId, data in self.cargo_data.items()
            if data["containerId"] == target_container and str(itemId) != target_itemId
        }
        
        # Build dependency graph
        blocking_items = []
        
        for itemId, item_data in items_in_container.items():
            item_start = item_data["position"]["startCoordinates"]
            item_end = item_data["position"]["endCoordinates"]
            item_priority = self.items_data[itemId]["priority"]
            
            # Check if item is in front of target (blocking)
            is_blocking = (
                # Item is in front of target (starts at a lower depth)
                item_start["depth"] < target_start["depth"] and
                # Width overlap (items are side by side)
                not (item_end["width"] <= target_start["width"] or 
                     item_start["width"] >= target_end["width"]) and
                # Priority check
                item_priority > target_priority
            )
            
            if is_blocking:
                blocking_items.append({
                    "itemId": itemId,
                    "name": self.items_data[itemId]["name"],
                    "position": item_data["position"],
                    "priority": item_priority
                })
        
        # If no blocking items, return empty list (0 steps needed)
        if not blocking_items:
            return []
        
        # Sort blocking items by depth (front to back)
        blocking_items.sort(key=lambda x: x["position"]["startCoordinates"]["depth"])
        
        # Generate retrieval steps
        steps = []
        step_number = 1
        
        # Remove blocking items (front to back)
        for item in blocking_items:
            steps.append({
                "step": step_number,
                "action": "remove",
                "itemId": int(item["itemId"]),
                "item_name": item["name"]
            })
            step_number += 1
        
        # Retrieve target item
        steps.append({
            "step": step_number,
            "action": "retrieve",
            "itemId": int(target_itemId),
            "item_name": self.items_data[target_itemId]["name"]
        })
        step_number += 1
        
        # Place back blocking items (back to front)
        for item in reversed(blocking_items):
            steps.append({
                "step": step_number,
                "action": "place",
                "itemId": int(item["itemId"]),
                "item_name": item["name"]
            })
            step_number += 1
        
        return steps