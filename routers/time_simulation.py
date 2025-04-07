from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, model_validator
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Union
import polars as pl
import os

router = APIRouter(
    prefix="/api/simulate",
    tags=["time_simulation"],
)

class ItemUsage(BaseModel):
    itemId: Optional[Union[int, str]] = None
    name: Optional[str] = None

    @model_validator(mode='after')
    def validate_itemIdentifier(self) -> 'ItemUsage':
        if self.itemId is not None and isinstance(self.itemId, str) and not self.itemId.strip():
            self.itemId = None
        if self.itemId is None and (self.name is None or not self.name.strip()):
            raise ValueError("Either itemId or name must be provided")
        return self

class TimeSimulationRequest(BaseModel):
    numOfDays: Optional[int] = None
    toTimestamp: Optional[str] = None
    itemsToBeUsedPerDay: List[ItemUsage]

@router.post("/day")
async def simulate_day(request: TimeSimulationRequest):
    try:
        if not os.path.exists("temp_imported_items.csv"):
            return {
                "success": False,
                "error": "Imported items data not found"
            }
        
        items_df = pl.read_csv("temp_imported_items.csv")
        current_date = datetime.now(timezone.utc)

        # Handle empty or invalid dates
        items_df = items_df.with_columns([
            pl.when(pl.col("expiryDate").is_null() | (pl.col("expiryDate") == ""))
            .then(None)
            .otherwise(pl.col("expiryDate"))
            .alias("expiryDate")
        ])

        # Calculate simulation duration
        if request.toTimestamp and request.toTimestamp.strip():
            try:
                # Handle both Z and ISO formats
                target_date = parse_datetime(request.toTimestamp)
                days_to_simulate = (target_date - current_date).days
            except ValueError as e:
                print(f"Error parsing timestamp: {e}")
                days_to_simulate = request.numOfDays if request.numOfDays else 1
                target_date = current_date + timedelta(days=days_to_simulate)
        else:
            days_to_simulate = request.numOfDays if request.numOfDays else 1
            target_date = current_date + timedelta(days=days_to_simulate)

        if days_to_simulate < 0:
            days_to_simulate = 1
            target_date = current_date + timedelta(days=1)

        items_used = []
        items_expired = []
        items_depleted_today = []

        # Process each day
        for day in range(days_to_simulate):
            current_date += timedelta(days=1)
            
            # Check expiry dates
            for item in items_df.to_dicts():
                if item["expiryDate"]:
                    try:
                        expiryDate = parse_expiryDate(item["expiryDate"])
                        if expiryDate.date() <= current_date.date():
                            items_expired.append({
                                "itemId": int(item["itemId"]),
                                "name": str(item["name"])
                            })
                            items_df = items_df.filter(pl.col("itemId") != item["itemId"])
                            continue
                    except ValueError:
                        continue
            
            # Process daily item usage
            for item_usage in request.itemsToBeUsedPerDay:
                filter_expr = []
                if item_usage.itemId is not None:
                    filter_expr.append(pl.col("itemId").cast(str) == str(item_usage.itemId))
                if item_usage.name and item_usage.name.strip():
                    filter_expr.append(pl.col("name") == item_usage.name)
                
                if not filter_expr:
                    continue
                
                matching_items = items_df.filter(pl.any_horizontal(filter_expr))
                
                for item in matching_items.to_dicts():
                    current_uses = int(item["usageLimit"])
                    new_uses = max(0, current_uses - 1)
                    
                    items_df = items_df.with_columns([
                        pl.when(pl.col("itemId").cast(str) == str(item["itemId"]))
                        .then(new_uses)
                        .otherwise(pl.col("usageLimit"))
                        .alias("usageLimit")
                    ])
                    
                    # Only store the final state of each item
                    if day == days_to_simulate - 1:
                        items_used.append({
                            "itemId": int(item["itemId"]),
                            "name": str(item["name"]),
                            "remainingUses": new_uses
                        })
                    
                    if current_uses > 0 and new_uses == 0:
                        items_depleted_today.append({
                            "itemId": int(item["itemId"]),
                            "name": str(item["name"])
                        })

        # Return UTC ISO format with Z
        target_date_iso = target_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        return {
            "success": True,
            "newDate": target_date_iso,
            "changes": {
                "itemsUsed": items_used,
                "itemsExpired": items_expired,
                "itemsDepletedToday": items_depleted_today
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def parse_datetime(date_str: str) -> datetime:
    """
    Parse datetime string in various formats including ISO and Z-format UTC timestamps.
    Returns a datetime object with UTC timezone.
    """
    try:
        # Try parsing as ISO format with timezone
        if '+' in date_str or '-' in date_str[10:]:  # Check if timezone info is present
            return datetime.fromisoformat(date_str).astimezone(timezone.utc)
        # Handle Z format (UTC)
        elif date_str.endswith('Z'):
            return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        # Simple ISO format without timezone (assume UTC)
        else:
            return datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
    except Exception as e:
        raise ValueError(f"Failed to parse datetime '{date_str}': {str(e)}")

def parse_expiryDate(date_str: str) -> datetime:
    """Parse date string in either YYYY-MM-DD or DD-MM-YY format."""
    try:
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            day, month, year = date_str.split('-')
            if len(year) == 2:
                year = f"20{year}"
            return datetime(int(year), int(month), int(day))
    except Exception:
        raise ValueError(f"Invalid date format: {date_str}")