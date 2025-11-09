#!/usr/bin/env python3
"""
Time/Date MCP Server - Provides time and date operations via MCP protocol
Uses Python's datetime and pytz libraries (no external API required)
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List
from pathlib import Path
from zoneinfo import ZoneInfo
import pytz

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Initialize the MCP server
server = Server("time-date-mcp-server")


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available time/date tools."""
    return [
        Tool(
            name="get_current_time",
            description="Get the current time in a specific timezone or UTC",
            inputSchema={
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "Timezone name (e.g., 'America/New_York', 'Europe/London', 'Asia/Tokyo') or 'UTC'. Defaults to 'UTC'",
                        "default": "UTC"
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format: 'iso' (ISO 8601), 'readable' (human-readable), or 'timestamp' (Unix timestamp). Default: 'readable'",
                        "default": "readable",
                        "enum": ["iso", "readable", "timestamp"]
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="convert_timezone",
            description="Convert a time from one timezone to another",
            inputSchema={
                "type": "object",
                "properties": {
                    "time": {
                        "type": "string",
                        "description": "Time string in ISO 8601 format (e.g., '2024-01-15T10:30:00') or 'now' for current time"
                    },
                    "from_timezone": {
                        "type": "string",
                        "description": "Source timezone (e.g., 'America/New_York', 'UTC')"
                    },
                    "to_timezone": {
                        "type": "string",
                        "description": "Target timezone (e.g., 'Europe/London', 'Asia/Tokyo', 'UTC')"
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format: 'iso' or 'readable'. Default: 'readable'",
                        "default": "readable",
                        "enum": ["iso", "readable"]
                    }
                },
                "required": ["from_timezone", "to_timezone"]
            }
        ),
        Tool(
            name="calculate_date_difference",
            description="Calculate the difference between two dates",
            inputSchema={
                "type": "object",
                "properties": {
                    "date1": {
                        "type": "string",
                        "description": "First date in ISO 8601 format (e.g., '2024-01-15' or '2024-01-15T10:30:00')"
                    },
                    "date2": {
                        "type": "string",
                        "description": "Second date in ISO 8601 format (e.g., '2024-02-20' or '2024-02-20T15:45:00') or 'now' for current time"
                    },
                    "unit": {
                        "type": "string",
                        "description": "Unit for the difference: 'days', 'hours', 'minutes', 'seconds', or 'all'. Default: 'days'",
                        "default": "days",
                        "enum": ["days", "hours", "minutes", "seconds", "all"]
                    }
                },
                "required": ["date1", "date2"]
            }
        ),
        Tool(
            name="add_subtract_time",
            description="Add or subtract time from a given date",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Base date in ISO 8601 format (e.g., '2024-01-15T10:30:00') or 'now' for current time"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to add (positive) or subtract (negative). Default: 0",
                        "default": 0
                    },
                    "hours": {
                        "type": "integer",
                        "description": "Number of hours to add (positive) or subtract (negative). Default: 0",
                        "default": 0
                    },
                    "minutes": {
                        "type": "integer",
                        "description": "Number of minutes to add (positive) or subtract (negative). Default: 0",
                        "default": 0
                    },
                    "seconds": {
                        "type": "integer",
                        "description": "Number of seconds to add (positive) or subtract (negative). Default: 0",
                        "default": 0
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format: 'iso' or 'readable'. Default: 'readable'",
                        "default": "readable",
                        "enum": ["iso", "readable"]
                    }
                },
                "required": ["date"]
            }
        ),
        Tool(
            name="format_date",
            description="Format a date string in different formats",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date string in ISO 8601 format (e.g., '2024-01-15T10:30:00') or 'now' for current time"
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format: 'iso', 'readable', 'short', 'long', or 'timestamp'. Default: 'readable'",
                        "default": "readable",
                        "enum": ["iso", "readable", "short", "long", "timestamp"]
                    },
                    "timezone": {
                        "type": "string",
                        "description": "Timezone for formatting (e.g., 'America/New_York', 'UTC'). Default: 'UTC'",
                        "default": "UTC"
                    }
                },
                "required": ["date"]
            }
        ),
        Tool(
            name="list_timezones",
            description="List available timezones or search for timezones by keyword",
            inputSchema={
                "type": "object",
                "properties": {
                    "search": {
                        "type": "string",
                        "description": "Optional keyword to search for in timezone names (e.g., 'New_York', 'London', 'Tokyo')"
                    },
                    "region": {
                        "type": "string",
                        "description": "Optional region filter: 'America', 'Europe', 'Asia', 'Africa', 'Australia', 'Pacific'"
                    }
                },
                "required": []
            }
        ),
    ]


def parse_datetime(date_str: str, timezone: str = "UTC") -> datetime:
    """Parse a date string into a datetime object."""
    if date_str.lower() == "now":
        tz = ZoneInfo(timezone) if timezone else ZoneInfo("UTC")
        return datetime.now(tz)
    
    # Try parsing ISO format
    try:
        # Try with timezone info
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        else:
            # Date only
            dt = datetime.fromisoformat(date_str)
            # If no timezone info, assume UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo(timezone))
        return dt
    except ValueError:
        # Try common formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=ZoneInfo(timezone))
                return dt
            except ValueError:
                continue
        raise ValueError(f"Unable to parse date string: {date_str}")


def get_timezone(tz_name: str) -> ZoneInfo:
    """Get timezone object, handling common aliases."""
    # Common aliases
    aliases = {
        "EST": "America/New_York",
        "PST": "America/Los_Angeles",
        "CST": "America/Chicago",
        "MST": "America/Denver",
        "GMT": "UTC",
    }
    
    tz_name = aliases.get(tz_name.upper(), tz_name)
    
    try:
        return ZoneInfo(tz_name)
    except Exception:
        # Fallback to pytz for older timezones
        try:
            return pytz.timezone(tz_name)
        except Exception:
            raise ValueError(f"Invalid timezone: {tz_name}")


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    try:
        if name == "get_current_time":
            timezone_str = arguments.get("timezone", "UTC")
            format_type = arguments.get("format", "readable")
            
            try:
                tz = get_timezone(timezone_str)
                now = datetime.now(tz)
                
                if format_type == "timestamp":
                    result = str(int(now.timestamp()))
                elif format_type == "iso":
                    result = now.isoformat()
                else:  # readable
                    result = f"Current time in {timezone_str}: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                
                return [TextContent(type="text", text=result)]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        elif name == "convert_timezone":
            time_str = arguments.get("time", "now")
            from_tz = arguments.get("from_timezone")
            to_tz = arguments.get("to_timezone")
            format_type = arguments.get("format", "readable")
            
            try:
                from_timezone = get_timezone(from_tz)
                to_timezone = get_timezone(to_tz)
                
                if time_str.lower() == "now":
                    dt = datetime.now(from_timezone)
                else:
                    dt = parse_datetime(time_str, from_tz)
                    # Ensure it's in the source timezone
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=from_timezone)
                    else:
                        dt = dt.astimezone(from_timezone)
                
                # Convert to target timezone
                converted = dt.astimezone(to_timezone)
                
                if format_type == "iso":
                    result = converted.isoformat()
                else:  # readable
                    result = f"{dt.strftime('%Y-%m-%d %H:%M:%S %Z')} ({from_tz}) = {converted.strftime('%Y-%m-%d %H:%M:%S %Z')} ({to_tz})"
                
                return [TextContent(type="text", text=result)]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        elif name == "calculate_date_difference":
            date1_str = arguments.get("date1")
            date2_str = arguments.get("date2", "now")
            unit = arguments.get("unit", "days")
            
            try:
                # Determine timezone from date strings if provided
                date1 = parse_datetime(date1_str)
                date2 = parse_datetime(date2_str)
                
                # Normalize to UTC for comparison
                if date1.tzinfo is None:
                    date1 = date1.replace(tzinfo=ZoneInfo("UTC"))
                if date2.tzinfo is None:
                    date2 = date2.replace(tzinfo=ZoneInfo("UTC"))
                
                diff = date2 - date1
                
                if unit == "all":
                    result = f"Difference between {date1_str} and {date2_str}:\n"
                    result += f"  Days: {diff.days}\n"
                    result += f"  Hours: {diff.total_seconds() / 3600:.2f}\n"
                    result += f"  Minutes: {diff.total_seconds() / 60:.2f}\n"
                    result += f"  Seconds: {diff.total_seconds():.2f}"
                elif unit == "days":
                    result = f"{diff.days} days"
                elif unit == "hours":
                    result = f"{diff.total_seconds() / 3600:.2f} hours"
                elif unit == "minutes":
                    result = f"{diff.total_seconds() / 60:.2f} minutes"
                else:  # seconds
                    result = f"{diff.total_seconds():.2f} seconds"
                
                return [TextContent(type="text", text=result)]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        elif name == "add_subtract_time":
            date_str = arguments.get("date", "now")
            days = arguments.get("days", 0)
            hours = arguments.get("hours", 0)
            minutes = arguments.get("minutes", 0)
            seconds = arguments.get("seconds", 0)
            format_type = arguments.get("format", "readable")
            
            try:
                dt = parse_datetime(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=ZoneInfo("UTC"))
                
                delta = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
                result_dt = dt + delta
                
                if format_type == "iso":
                    result = result_dt.isoformat()
                else:  # readable
                    operation = "added" if (days + hours + minutes + seconds) >= 0 else "subtracted"
                    result = f"Original: {dt.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
                    result += f"After {operation} {abs(days)} days, {abs(hours)} hours, {abs(minutes)} minutes, {abs(seconds)} seconds:\n"
                    result += f"Result: {result_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                
                return [TextContent(type="text", text=result)]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        elif name == "format_date":
            date_str = arguments.get("date")
            format_type = arguments.get("format", "readable")
            timezone_str = arguments.get("timezone", "UTC")
            
            try:
                dt = parse_datetime(date_str)
                tz = get_timezone(timezone_str)
                
                # Convert to target timezone
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=ZoneInfo("UTC"))
                dt = dt.astimezone(tz)
                
                if format_type == "iso":
                    result = dt.isoformat()
                elif format_type == "timestamp":
                    result = str(int(dt.timestamp()))
                elif format_type == "short":
                    result = dt.strftime("%Y-%m-%d")
                elif format_type == "long":
                    result = dt.strftime("%A, %B %d, %Y %I:%M:%S %p %Z")
                else:  # readable
                    result = dt.strftime("%Y-%m-%d %H:%M:%S %Z")
                
                return [TextContent(type="text", text=result)]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        elif name == "list_timezones":
            search = arguments.get("search", "")
            region = arguments.get("region", "")
            
            try:
                # Get all timezones
                all_tz = pytz.all_timezones
                
                # Filter by region if specified
                if region:
                    all_tz = [tz for tz in all_tz if tz.startswith(region + "/")]
                
                # Filter by search term if specified
                if search:
                    search_lower = search.lower()
                    all_tz = [tz for tz in all_tz if search_lower in tz.lower()]
                
                # Limit results
                all_tz = sorted(all_tz)[:50]  # Limit to 50 results
                
                if not all_tz:
                    result = "No timezones found matching the criteria."
                else:
                    result = f"Found {len(all_tz)} timezone(s):\n"
                    result += "\n".join(f"  - {tz}" for tz in all_tz)
                
                return [TextContent(type="text", text=result)]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error processing time/date request: {str(e)}")]


async def main():
    """Main entry point for the time/date MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

