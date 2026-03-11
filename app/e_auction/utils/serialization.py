from datetime import datetime

def datetime_to_utc_iso(dt: datetime) -> str:
    """
    Standardized UTC ISO 8601 formatter.
    Ensures 'naive' timestamps from the database are treated as UTC.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Append 'Z' for UTC if timezone is missing
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return dt.isoformat()

# Common ConfigDict to be reused across all schemas
UTC_JSON_CONFIG = {
    "json_encoders": {datetime: datetime_to_utc_iso}
}
