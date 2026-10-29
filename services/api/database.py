"""TinyDB database initialization and management."""

from tinydb import TinyDB
from pathlib import Path
from datetime import datetime

# Database path
DB_PATH = Path(__file__).parent / "suppliers.json"

# Global database instance
_db = None

def get_db() -> TinyDB:
    """Get database instance."""
    global _db
    if _db is None:
        _db = TinyDB(str(DB_PATH))
    return _db

def init_db():
    """Initialize database."""
    db = get_db()
    # Ensure suppliers table exists
    suppliers_table = db.table("suppliers")
    return suppliers_table

def close_db():
    """Close database connection."""
    global _db
    if _db is not None:
        _db.close()
        _db = None
