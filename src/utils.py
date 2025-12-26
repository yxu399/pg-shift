import os
import hashlib
import re
from dataclasses import dataclass
from typing import Dict, Optional

# Regex to parse: YYYYMMDDHHmmss_xxxx_description.up.sql
# Capture groups: 1=Timestamp, 2=Suffix, 3=Name, 4=Type (up/down)
FILENAME_REGEX = re.compile(r"^(\d{14})_([a-zA-Z0-9]{4})_(.+?)\.(up|down)\.sql$")

@dataclass
class MigrationFile:
    version: str      # Full ID: timestamp_suffix
    name: str         # description
    up_path: Optional[str] = None
    down_path: Optional[str] = None
    
    @property
    def up_checksum(self) -> str:
        """Calculates SHA256 of the UP file."""
        if not self.up_path:
            return None
        return calculate_file_hash(self.up_path)

def calculate_file_hash(filepath: str) -> str:
    """Reads a file in binary mode and returns its SHA256 hash."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(65536) # Read in 64k chunks
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()

def get_migrations(directory: str = "migrations") -> Dict[str, MigrationFile]:
    """
    Scans the directory and groups .up.sql and .down.sql files by version.
    Returns a dict: {'2023..._xxxx': MigrationFile object}
    """
    migrations = {}
    
    if not os.path.exists(directory):
        return migrations

    for filename in os.listdir(directory):
        match = FILENAME_REGEX.match(filename)
        if not match:
            continue
            
        timestamp, suffix, name, kind = match.groups()
        version = f"{timestamp}_{suffix}"
        
        if version not in migrations:
            migrations[version] = MigrationFile(version=version, name=name)
        
        full_path = os.path.join(directory, filename)
        
        if kind == 'up':
            migrations[version].up_path = full_path
        elif kind == 'down':
            migrations[version].down_path = full_path
            
    return migrations