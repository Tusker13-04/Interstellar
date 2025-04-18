from fastapi import APIRouter, HTTPException, Query, Depends
import polars as pl
import os
import re
from typing import Optional, List
from schemas import (
    Coordinates, 
    Position, 
    Item_for_search, 
    SearchResponse, 
    RetrievalStep,
    RetrieveItemRequest,  
    PlaceItemRequest,           
    PlaceItemResponse     
)
from datetime import datetime, timezone, timedelta
import csv
from algos.retrieve_algo import PriorityAStarRetrieval
from algos.search_algo import ItemSearchSystem
import numpy as np
import pandas as pd
import json

router = APIRouter(
    prefix="/api",
    tags=["logs"]
)

cargo_file = "cargo_arrangement.csv"
items_file = "space_cargo_management/imported_items.csv"
containers_file = "space_cargo_management/imported_containers.csv"

LOG_FILE = "logs.csv"

# DataFrame to store logs
log_columns = ["timestamp", "user_id", "action_type", "itemId", "details"]
logs_df = pl.DataFrame(schema={
    "timestamp": pl.Utf8,
    "user_id": pl.Utf8,
    "action_type": pl.Utf8,
    "itemId": pl.Int64,
    "details": pl.Utf8
})

# Create logs file if it doesn't exist
if not os.path.exists(LOG_FILE):
    # Create an empty DataFrame with the correct schema
    logs_df.write_csv(LOG_FILE)

def log_action(action_type: str, details: dict = None, user_id: str = "", itemId: int = 0, timestamp: str = None):
    global logs_df

    if not isinstance(details, dict):  # Ensure details is a dictionary
        details = {"message": str(details)}

    # Convert details to JSON string
    details_json = json.dumps(details)

    # Use provided timestamp or generate current timestamp
    if timestamp:
        # Convert from Z format to +00:00 format if needed
        timestamp = convert_timestamp(timestamp)
    else:
        timestamp = datetime.now(timezone.utc).isoformat()

    # Create new log entry with proper types
    new_entry = pl.DataFrame({
        "timestamp": [timestamp],
        "user_id": [str(user_id)],
        "action_type": [str(action_type)],
        "itemId": [int(itemId) if itemId is not None else 0],
        "details": [details_json]
    })

    # Load existing logs if file exists
    if os.path.exists(LOG_FILE):
        existing_logs = pl.read_csv(LOG_FILE)
        logs_df = pl.concat([existing_logs, new_entry], how="vertical")
    else:
        logs_df = new_entry

    # Save to CSV
    logs_df.write_csv(LOG_FILE)

def convert_timestamp(timestamp):
    """Convert various timestamp formats to a consistent +00:00 format."""
    if not timestamp:
        return timestamp
        
    try:
        # Remove any existing timezone info first
        if 'Z' in timestamp:
            timestamp = timestamp.replace('Z', '')
        elif '+' in timestamp:
            timestamp = timestamp.split('+')[0]
            
        # Handle the format like "12-03-2025T:00:00:00" or "12-03-2025T00:00:00"
        if 'T:' in timestamp:
            timestamp = timestamp.replace('T:', 'T')
            
        # Convert DD-MM-YYYY to YYYY-MM-DD if in that format
        if re.match(r'^\d{2}-\d{2}-\d{4}T', timestamp):
            date_part = timestamp.split('T')[0]
            time_part = timestamp.split('T')[1]
            day, month, year = date_part.split('-')
            timestamp = f"{year}-{month}-{day}T{time_part}"
            
        # Add timezone if not present
        if not any(x in timestamp for x in ['+', '-', 'Z']):
            timestamp = timestamp + '+00:00'
            
        return timestamp
    except Exception as e:
        raise ValueError(f"Invalid timestamp format: {timestamp}")

def parse_datetime(timestamp_str):
    """Parse datetime from various formats."""
    if not timestamp_str:
        return None
        
    timestamp_str = convert_timestamp(timestamp_str)
    try:
        return datetime.fromisoformat(timestamp_str)
    except ValueError as e:
        raise ValueError(f"Could not parse datetime from {timestamp_str}: {str(e)}")

@router.get("/logs")
async def get_logs(
    startDate: Optional[str] = Query(None, description="Start date in ISO format"),
    endDate: Optional[str] = Query(None, description="End date in ISO format"),
    itemId: Optional[int] = Query(None, description="Filter by item ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    action_type: Optional[str] = Query(None, description="Filter by action type")
):
    try:
        # Check if log file exists
        if not os.path.exists(LOG_FILE):
            return {"logs": []}

        # Load logs from CSV
        logs_df = pl.read_csv(LOG_FILE)

        # Print column names for debugging
        print(f"Columns in logs_df: {logs_df.columns}")

        # Convert timestamps to datetime objects with UTC timezone
        logs_df = logs_df.with_columns(
            pl.col("timestamp").str.strptime(pl.Datetime, format="%Y-%m-%dT%H:%M:%S%.f%z").cast(pl.Datetime("us", "UTC"))
        )

        # Parse date filters
        if startDate:
            try:
                start_dt = parse_datetime(startDate)
                # Convert to UTC aware datetime for comparison
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                else:
                    start_dt = start_dt.astimezone(timezone.utc)
                logs_df = logs_df.filter(pl.col("timestamp") >= pl.lit(start_dt).cast(pl.Datetime("us", "UTC")))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid start date format: {str(e)}")

        if endDate:
            try:
                end_dt = parse_datetime(endDate)
                # Convert to UTC aware datetime for comparison
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=timezone.utc)
                else:
                    end_dt = end_dt.astimezone(timezone.utc)
                logs_df = logs_df.filter(pl.col("timestamp") <= pl.lit(end_dt).cast(pl.Datetime("us", "UTC")))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid end date format: {str(e)}")

        if itemId is not None:
            logs_df = logs_df.filter(pl.col("itemId") == itemId)

        if user_id:
            logs_df = logs_df.filter(pl.col("user_id") == user_id)

        if action_type:
            logs_df = logs_df.filter(pl.col("action_type") == action_type)

        # Convert back to list of dictionaries
        logs = []
        for row in logs_df.iter_rows(named=True):
            # Parse the details JSON string
            try:
                details = json.loads(row["details"])
            except json.JSONDecodeError:
                details = {"message": row["details"]}

            # Use get() to safely access columns that might not exist
            log_entry = {
                "timestamp": row["timestamp"].isoformat(),
                "user_id": row.get("user_id", ""),
                "action_type": row.get("action_type", ""),
                "itemId": row.get("itemId", 0),
                "details": details
            }
            logs.append(log_entry)

        return {"logs": logs}

    except Exception as e:
        print(f"Error in get_logs: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear")
async def clear_logs():
    """Clear all logs and delete imported files."""
    try:
        # Delete the log file
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
            # Reinitialize empty logs DataFrame
            logs_df = pl.DataFrame(schema={
                "timestamp": pl.Utf8,
                "user_id": pl.Utf8,
                "action_type": pl.Utf8,
                "itemId": pl.Int64,
                "details": pl.Utf8
            })
            logs_df.write_csv(LOG_FILE)

        # Delete imported files
        files_to_delete = [
            "imported_containers.csv",
            "imported_items.csv",
            "cargo_arrangement.csv"
        ]

        for file in files_to_delete:
            if os.path.exists(file):
                os.remove(file)

        return {"success": True, "message": "Logs and imported files cleared successfully"}
    except Exception as e:
        print(f"Error clearing logs and files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/logs")
async def add_log_entry(
    action_type: str,
    itemId: Optional[int] = None,
    user_id: Optional[str] = None,
    timestamp: Optional[str] = None,
    details: Optional[dict] = None
):
    """Add a log entry with the given parameters."""
    try:
        # Convert timestamp if needed
        if timestamp and timestamp.endswith('Z'):
            timestamp = convert_timestamp(timestamp)
            
        # Log the action
        log_action(
            action_type=action_type,
            itemId=itemId,
            user_id=user_id,
            timestamp=timestamp,
            details=details or {}
        )
        
        return {"success": True, "message": "Log entry added successfully"}
    except Exception as e:
        print(f"Error adding log entry: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))