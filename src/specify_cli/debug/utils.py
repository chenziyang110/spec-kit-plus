import re
import subprocess
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

def run_command(cmd: str) -> str:
    """
    Executes a shell command and returns the combined stdout and stderr.
    """
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
        parts = []
        if result.stdout:
            parts.append(result.stdout.strip())
        if result.stderr:
            parts.append(result.stderr.strip())
        if result.returncode != 0:
            parts.append(f"Command exited with code {result.returncode}")
        return "\n".join(part for part in parts if part).strip()
    except Exception as e:
        return f"Error executing command: {str(e)}"

def edit_file(path: str, content: str):
    """
    Overwrites the file at path with the provided content.
    """
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")

def read_file(path: str) -> str:
    """
    Reads and returns the content of the file at path.
    """
    file_path = Path(path)
    if not file_path.exists():
        return f"Error: File not found at {path}"
    return file_path.read_text(encoding="utf-8")

def get_debug_dir() -> Path:
    """
    Returns the path to .planning/debug/, ensuring it exists.
    """
    # Assuming the project root is where the command is run
    debug_dir = Path(".planning/debug")
    debug_dir.mkdir(parents=True, exist_ok=True)
    return debug_dir
