from typing import List, Dict, Tuple, Optional
from datetime import datetime
import polars as pl
import json

def load_waste_items(filename: Optional[str] = None) -> List[Dict]:
    """
    Load waste items from CSV file.
    
    Args:
        filename: Optional path to the waste items CSV file. Defaults to "waste_items.csv".
        
    Returns:
        List of waste items with their properties
    """
    try:
        file_to_load = filename or "waste_items.csv"
        waste_items_df = pl.read_csv(file_to_load)
        waste_items = []
        
        for item in waste_items_df.to_dicts():
            # Convert field names to match the expected format
            waste_item = {
                "itemId": str(item.get("itemId", "")),
                "name": str(item.get("name", "")),
                "reason": str(item.get("reason", "")),
                "containerId": str(item.get("containerId", "")),
                "position": str(item.get("position", "")),
                "retrieval_steps": item.get("retrieval_steps", "[]")
            }
            waste_items.append(waste_item)
            
        return waste_items
    except Exception as e:
        print(f"Error loading waste items: {str(e)}")
        return []

def load_imported_items(filename: Optional[str] = None) -> Dict[str, Dict]:
    """
    Load imported items from CSV file.
    
    Args:
        filename: Optional path to the imported items CSV file. Defaults to "imported_items.csv".
        
    Returns:
        Dictionary mapping itemId to item properties
    """
    try:
        file_to_load = filename or "imported_items.csv"
        imported_items_df = pl.read_csv(file_to_load)
        return {str(item["itemId"]): item for item in imported_items_df.to_dicts()}
    except Exception as e:
        print(f"Error loading imported items: {str(e)}")
        return {}

def link_waste_with_imported_items(waste_items: List[Dict], imported_items: Dict[str, Dict]) -> List[Dict]:
    """
    Link waste items with their properties from imported items.
    
    Args:
        waste_items: List of waste items
        imported_items: Dictionary mapping itemId to item properties
        
    Returns:
        List of waste items with additional properties from imported items
    """
    linked_items = []
    
    for waste_item in waste_items:
        item_id = str(waste_item["itemId"])
        
        if item_id in imported_items:
            # Create a new dictionary with combined properties
            linked_item = {**waste_item}
            
            # Add properties from imported items
            imported_item = imported_items[item_id]
            linked_item["width"] = float(imported_item.get("width", 0))
            linked_item["depth"] = float(imported_item.get("depth", 0))
            linked_item["height"] = float(imported_item.get("height", 0))
            linked_item["mass"] = float(imported_item.get("mass", 0))
            linked_item["priority"] = int(imported_item.get("priority", 0))
            linked_item["expiryDate"] = str(imported_item.get("expiryDate", ""))
            linked_item["usageLimit"] = int(imported_item.get("usageLimit", 0))
            
            # Calculate volume
            linked_item["volume"] = linked_item["width"] * linked_item["depth"] * linked_item["height"]
            
            linked_items.append(linked_item)
        else:
            # If item not found in imported items, add default values
            linked_item = {**waste_item}
            linked_item["width"] = 0.0
            linked_item["depth"] = 0.0
            linked_item["height"] = 0.0
            linked_item["mass"] = 0.0
            linked_item["priority"] = 0
            linked_item["expiryDate"] = ""
            linked_item["usageLimit"] = 0
            linked_item["volume"] = 0.0
            linked_items.append(linked_item)
    
    return linked_items

def select_waste_items_greedy(waste_items: List[Dict], max_weight: float) -> Tuple[List[Dict], float]:
    """
    Select waste items for undocking using a greedy approach that prioritizes
    heavier items within weight constraints.
    
    Args:
        waste_items: List of waste items with their properties
        max_weight: Maximum weight allowed for the undocking container
        
    Returns:
        selected_items: List of selected waste items
        total_weight: Total weight of selected items
    """
    # Sort items by when they became waste (earlier items first)
    sorted_items = sorted(waste_items, key=lambda x: int(x["itemId"]))
    
    # Get weights from items
    weights = []
    for item in sorted_items:
        if "mass" in item:
            weights.append(item["mass"])
        else:
            weights.append(0)
    
    # Create a simple greedy solution - try to fit as many heavy items as possible
    # Sort items by weight in descending order
    indices = sorted(range(len(weights)), key=lambda i: weights[i], reverse=True)
    
    selected = []
    remaining_weight = max_weight
    
    for idx in indices:
        if weights[idx] <= remaining_weight:
            selected.append(sorted_items[idx])
            remaining_weight -= weights[idx]
    
    # Sort selected items by itemId to maintain original priority
    selected.sort(key=lambda x: int(x["itemId"]))
    
    # Calculate total weight of selected items
    total_weight = sum(item.get("mass", 0) for item in selected)
    
    return selected, total_weight

def generate_return_plan(selected_items: List[Dict], undocking_container_id: str) -> Tuple[List[Dict], List[Dict]]:
    """
    Generate return plan and retrieval steps for selected waste items.
    
    Args:
        selected_items: List of selected waste items
        undocking_container_id: ID of the undocking container
        
    Returns:
        return_plan: List of steps for moving items to undocking container
        retrieval_steps: List of detailed steps for retrieving each item
    """
    return_plan = []
    retrieval_steps = []
    step_counter = 1
    
    # Process each selected waste item
    for item in selected_items:
        item_id = str(item["itemId"])
        item_name = item["name"]
        container_id = item["containerId"]
        waste_container = f"waste_{container_id}"
        
        # Add retrieval step
        retrieval_steps.append({
            "step": step_counter,
            "action": "retrieve",
            "itemId": item_id,
            "itemName": item_name
        })
        step_counter += 1
        
        # Add step to move waste to its waste container
        return_plan.append({
            "step": len(return_plan) + 1,
            "itemId": item_id,
            "itemName": item_name,
            "fromContainer": container_id,
            "toContainer": waste_container
        })
    
    return return_plan, retrieval_steps

def create_return_manifest(selected_items: List[Dict], undocking_container_id: str, 
                          undocking_date: str, total_weight: float) -> Dict:
    """
    Create return manifest for the undocking container.
    
    Args:
        selected_items: List of selected waste items
        undocking_container_id: ID of the undocking container
        undocking_date: Date of undocking
        total_weight: Total weight of selected items
        
    Returns:
        Dictionary containing the return manifest
    """
    return_items = []
    total_volume = 0
    
    # Use a set to track added item IDs to prevent duplicates
    added_item_ids = set()
    
    for item in selected_items:
        item_id = str(item["itemId"])
        
        # Only add the item if it hasn't been added before
        if item_id not in added_item_ids:
            return_items.append({
                "itemId": item_id,
                "name": item["name"],
                "reason": item["reason"]
            })
            
            # Add the item ID to the set of added items
            added_item_ids.add(item_id)
            
            # Calculate volume
            volume = item.get("volume", 0)
            if volume == 0:
                volume = item.get("width", 0) * item.get("depth", 0) * item.get("height", 0)
            
            total_volume += volume
    
    # Round total weight to 2 decimal places
    total_weight_rounded = round(total_weight, 2)
    
    return {
        "undockingContainerId": undocking_container_id,
        "undockingDate": undocking_date,
        "returnItems": return_items,
        "totalVolume": total_volume,
        "totalWeight": total_weight_rounded
    } 