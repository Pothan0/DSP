import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json
import hashlib
import sqlite3

import config


class AuditStore:
    """
    Module 4: Cryptographic Audit Store
    Append-only SQLite database with SHA-256 hash chain for tamper detection.
    """
    
    def __init__(self, db_file: str = None):
        self.db_file = db_file or config.DB_FILE
        self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
        self._init_tables()
    
    def _init_tables(self):
        """Create audit log table if it doesn't exist."""
        cur = self.conn.cursor()
        
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {config.AUDIT_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                sender TEXT,
                prev_hash TEXT NOT NULL,
                this_hash TEXT NOT NULL
            )
        """)
        
        self.conn.commit()
    
    def _get_last_hash(self) -> str:
        """Get the hash of the last audit entry, or GENESIS if none."""
        cur = self.conn.cursor()
        cur.execute(f"""
            SELECT this_hash FROM {config.AUDIT_TABLE}
            ORDER BY id DESC LIMIT 1
        """)
        row = cur.fetchone()
        return row[0] if row else "GENESIS"
    
    def write(
        self,
        event_type: str,
        payload: dict,
        sender: str = None
    ) -> str:
        """
        Append a new event to the audit log.
        Returns the hash of the new entry.
        """
        timestamp = datetime.utcnow().isoformat()
        payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        
        prev_hash = self._get_last_hash()
        
        raw = f"{prev_hash}|{timestamp}|{event_type}|{payload_json}"
        this_hash = hashlib.sha256(raw.encode()).hexdigest()
        
        cur = self.conn.cursor()
        cur.execute(f"""
            INSERT INTO {config.AUDIT_TABLE}
            (timestamp, event_type, payload_json, sender, prev_hash, this_hash)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (timestamp, event_type, payload_json, sender, prev_hash, this_hash))
        
        self.conn.commit()
        
        return this_hash
    
    def log_event(self, event_type: str, payload: dict = None, sender: str = None) -> str:
        """Alias for write to match verification test."""
        if payload is None:
            payload = {}
        if isinstance(event_type, str) and payload == {}:
            payload = {"event": event_type}
        return self.write(event_type, payload, sender)
    
    def verify_chain(self) -> bool:
        """
        Verify the integrity of the entire audit chain.
        Returns True if chain is intact, False if tampered.
        """
        cur = self.conn.cursor()
        
        cur.execute(f"""
            SELECT id, timestamp, event_type, payload_json, sender, prev_hash, this_hash
            FROM {config.AUDIT_TABLE}
            ORDER BY id ASC
        """)
        
        rows = cur.fetchall()
        
        prev_hash = "GENESIS"
        
        for row in rows:
            _, timestamp, event_type, payload_json, sender, stored_prev_hash, stored_this_hash = row
            
            if stored_prev_hash != prev_hash:
                print(f"Chain broken at id={row[0]}: prev_hash mismatch")
                return False
            
            raw = f"{stored_prev_hash}|{timestamp}|{event_type}|{payload_json}"
            computed_hash = hashlib.sha256(raw.encode()).hexdigest()
            
            if computed_hash != stored_this_hash:
                print(f"Chain broken at id={row[0]}: hash mismatch")
                return False
            
            prev_hash = stored_this_hash
        
        return True
    
    def query(
        self,
        sender: str = None,
        event_type: str = None,
        since: datetime = None
    ) -> List[dict]:
        """
        Query audit logs with optional filters.
        """
        cur = self.conn.cursor()
        
        conditions = []
        params = []
        
        if sender:
            conditions.append("sender = ?")
            params.append(sender)
        
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        
        if since:
            conditions.append("timestamp >= ?")
            params.append(since.isoformat())
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        cur.execute(f"""
            SELECT id, timestamp, event_type, payload_json, sender, this_hash
            FROM {config.AUDIT_TABLE}
            WHERE {where_clause}
            ORDER BY id DESC
            LIMIT 100
        """, params)
        
        rows = cur.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "timestamp": row[1],
                "event_type": row[2],
                "payload": json.loads(row[3]),
                "sender": row[4],
                "hash": row[5][:12] + "..."
            })
        
        return results
    
    def get_stats(self) -> dict:
        """Get aggregate statistics."""
        cur = self.conn.cursor()
        
        cur.execute(f"SELECT COUNT(*) FROM {config.AUDIT_TABLE}")
        total = cur.fetchone()[0]
        
        cur.execute(f"""
            SELECT event_type, COUNT(*) 
            FROM {config.AUDIT_TABLE} 
            GROUP BY event_type
        """)
        event_counts = dict(cur.fetchall())
        
        return {
            "total_events": total,
            "event_counts": event_counts
        }


# Global audit store instance
_store: Optional[AuditStore] = None


def get_audit_store() -> AuditStore:
    """Get or create the global audit store instance."""
    global _store
    if _store is None:
        _store = AuditStore()
    return _store


def init_audit_store() -> AuditStore:
    """Initialize and return the audit store."""
    global _store
    _store = AuditStore()
    
    if not _store.verify_chain():
        raise RuntimeError("CRITICAL: Audit chain verification failed on startup!")
    
    return _store