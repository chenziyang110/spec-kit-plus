import re
from pathlib import Path
from datetime import datetime

def generate_slug(trigger: str) -> str:
    """
    Sanitizes trigger and prepends a timestamp.
    Example: 'API Timeout' -> '202310271030-api-timeout'
    """
    # Sanitize: lowercase, remove special characters, replace spaces with hyphens
    sanitized = trigger.lower()
    sanitized = re.sub(r'[^a-z0-9\s-]', '', sanitized)
    sanitized = re.sub(r'\s+', '-', sanitized).strip('-')
    
    # Prepend timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    return f"{timestamp}-{sanitized}"

def get_debug_dir() -> Path:
    """
    Returns the path to .planning/debug/, ensuring it exists.
    """
    # Assuming the project root is where the command is run
    debug_dir = Path(".planning/debug")
    debug_dir.mkdir(parents=True, exist_ok=True)
    return debug_dir
