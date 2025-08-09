"""
Database management for Time Capsule AI
"""

import sqlite3
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db_dir = Path(db_path).parent
        self.db_dir.mkdir(exist_ok=True)
    
    async def initialize(self):
        """Initialize the database with required tables"""
        await self._execute_script(self._get_schema_sql())
        print(f"✅ Database initialized at {self.db_path}")
    
    def _get_schema_sql(self) -> str:
        """Get the complete database schema"""
        return """
        -- Users table
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            phone_number TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tone_profile TEXT, -- JSON
            preferences TEXT,  -- JSON
            timezone TEXT DEFAULT 'UTC'
        );

        -- Reminders table
        CREATE TABLE IF NOT EXISTS reminders (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id),
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            due_at TIMESTAMP,
            completed_at TIMESTAMP,
            emotional_context TEXT, -- JSON
            activity_context TEXT,  -- JSON
            location_context TEXT,  -- JSON
            delivery_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            user_response_history TEXT -- JSON
        );

        -- Timeline entries table
        CREATE TABLE IF NOT EXISTS timeline_entries (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            entry_type TEXT NOT NULL,
            content TEXT NOT NULL,
            emotional_state TEXT, -- JSON
            context_data TEXT,    -- JSON
            searchable_text TEXT,
            tags TEXT, -- JSON array
            related_entries TEXT -- JSON array
        );

        -- Time capsules table
        CREATE TABLE IF NOT EXISTS time_capsules (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id),
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            earliest_delivery TIMESTAMP,
            latest_delivery TIMESTAMP,
            delivered_at TIMESTAMP,
            emotional_snapshot TEXT, -- JSON
            context_snapshot TEXT    -- JSON
        );

        -- Interactions table (for learning)
        CREATE TABLE IF NOT EXISTS interactions (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            interaction_type TEXT,
            user_message TEXT,
            system_response TEXT,
            user_feedback TEXT,
            response_time_seconds INTEGER,
            tone_used TEXT -- JSON
        );

        -- Scheduled nudges table
        CREATE TABLE IF NOT EXISTS scheduled_nudges (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id),
            scheduled_time TIMESTAMP NOT NULL,
            nudge_type TEXT NOT NULL, -- 'daily', 'contextual'
            context TEXT, -- JSON
            trigger_message TEXT,
            delivered INTEGER DEFAULT 0,
            delivered_at TIMESTAMP
        );

        -- Nudge interactions table (for learning)
        CREATE TABLE IF NOT EXISTS nudge_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT REFERENCES users(id),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            context_data TEXT, -- JSON
            response_quality INTEGER, -- Response length as quality indicator
            emotional_response TEXT
        );

        -- Create indexes for better performance
        CREATE INDEX IF NOT EXISTS idx_reminders_user_due ON reminders(user_id, due_at);
        CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders(status);
        CREATE INDEX IF NOT EXISTS idx_timeline_user_timestamp ON timeline_entries(user_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_timeline_searchable ON timeline_entries(searchable_text);
        CREATE INDEX IF NOT EXISTS idx_capsules_delivery ON time_capsules(user_id, earliest_delivery, latest_delivery);
        CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions(user_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_nudges_user_time ON scheduled_nudges(user_id, scheduled_time);
        CREATE INDEX IF NOT EXISTS idx_nudges_delivered ON scheduled_nudges(delivered, scheduled_time);

        -- Full-text search for timeline entries
        CREATE VIRTUAL TABLE IF NOT EXISTS timeline_fts USING fts5(
            entry_id,
            content,
            searchable_text,
            tags
        );
        """
    
    async def _execute_script(self, script: str):
        """Execute a SQL script asynchronously"""
        def _execute():
            conn = sqlite3.connect(self.db_path)
            conn.executescript(script)
            conn.commit()
            conn.close()
        
        await asyncio.get_event_loop().run_in_executor(None, _execute)
    
    async def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results as dictionaries"""
        def _execute():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return results
        
        return await asyncio.get_event_loop().run_in_executor(None, _execute)
    
    async def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows"""
        def _execute():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query, params)
            affected_rows = cursor.rowcount
            conn.commit()
            conn.close()
            return affected_rows
        
        return await asyncio.get_event_loop().run_in_executor(None, _execute)
    
    async def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute multiple queries with different parameters"""
        def _execute():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            affected_rows = cursor.rowcount
            conn.commit()
            conn.close()
            return affected_rows
        
        return await asyncio.get_event_loop().run_in_executor(None, _execute)
    
    def serialize_json(self, data: Any) -> str:
        """Serialize data to JSON string for database storage"""
        if data is None:
            return None
        return json.dumps(data, default=str)
    
    def deserialize_json(self, json_str: str) -> Any:
        """Deserialize JSON string from database"""
        if json_str is None:
            return None
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return None
    
    async def get_user_or_create(self, user_id: str, phone_number: str = None) -> Dict[str, Any]:
        """Get user or create if doesn't exist"""
        # Try to get existing user
        users = await self.execute_query(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        )
        
        if users:
            return users[0]
        
        # Create new user
        await self.execute_update(
            """INSERT INTO users (id, phone_number, created_at) 
               VALUES (?, ?, ?)""",
            (user_id, phone_number or user_id, datetime.now())
        )
        
        # Return the created user
        users = await self.execute_query(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        )
        return users[0] if users else None