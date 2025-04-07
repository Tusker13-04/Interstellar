from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
import polars as pl
from fastapi.responses import JSONResponse

router = APIRouter()

class ItemUsage(BaseModel):
    itemId: Union[int, str]
    usageCount: int = 1

class TimeSimulationRequest(BaseModel):
    itemsToBeUsedPerDay: Optional[List[Dict[str, Any]]] = None

@router.post("/simulate/day")
async def simulate_day(request: TimeSimulationRequest):
    """Simulate the passage of a day and update item states."""
    try:
        print("\nStarting day simulation...")
        print(f"Request data: {request}")
        
        # Load current items data
        items_df = pl.read_csv("imported_items.csv")
        print(f"Loaded {len(items_df)} items")
        print(f"Available columns: {items_df.columns}")
        print(f"Available item IDs: {items_df['itemId'].to_list()[:10]}...")  # Show first 10 item IDs
        
        items_used = []
        items_depleted = []
        
        # Track usage for items that were used
        if request.itemsToBeUsedPerDay:
            print(f"Processing {len(request.itemsToBeUsedPerDay)} items to be used")
            for item_usage in request.itemsToBeUsedPerDay:
                item_id = str(item_usage.get("itemId", ""))
                usage_count = int(item_usage.get("usageCount", 1))
                print(f"Processing item {item_id} with usage count {usage_count}")
                
                # Find the item in the DataFrame
                item_row = items_df.filter(pl.col("itemId").cast(str) == item_id)
                if len(item_row) > 0:
                    item_name = item_row["name"][0]
                    current_usage = int(item_row["usageLimit"][0])
                    print(f"Found item: {item_name} with current usage limit {current_usage}")
                    
                    # Add to items used list
                    items_used.append({
                        "itemId": int(item_id),
                        "name": item_name,
                        "usageCount": usage_count
                    })
                    
                    # Check if item would be depleted
                    if current_usage <= usage_count:
                        print(f"Item {item_name} would be depleted")
                        items_depleted.append({
                            "itemId": int(item_id),
                            "name": item_name
                        })
                else:
                    print(f"Warning: Item ID {item_id} not found in database")
        else:
            print("No items to be used in request")
        
        # Check for expired items
        current_date = datetime.now().date()
        print(f"Current date: {current_date}")
        
        # Get expired items
        expired_items = items_df.filter(
            (pl.col("expiryDate").is_not_null()) & 
            (pl.col("expiryDate").str.len_chars() > 0) &
            (pl.col("expiryDate").str.strptime(pl.Date, format="%d-%m-%y", strict=False) < current_date)
        )
        
        items_expired = [
            {
                "itemId": row["itemId"],
                "name": row["name"]
            }
            for row in expired_items.iter_rows(named=True)
        ]
        print(f"Found {len(items_expired)} expired items")
        
        return {
            "success": True,
            "newDate": datetime.now().isoformat(),
            "changes": {
                "itemsUsed": items_used,
                "itemsExpired": items_expired,
                "itemsDepletedToday": items_depleted
            }
        }
        
    except Exception as e:
        print(f"Error in day simulation: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {"success": False, "error": str(e)}