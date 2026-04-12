import sqlite3
import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
import aiosqlite

from config import get_config


class AuditStore:
    """
    Cryptographic audit chain with tamper-evident logging.
    Each record includes: id, seq, ts, event_type, session_id, tool, arguments_hash, 
    trust_score, flags, decision, prev_hash, this_hash
    """
    
    def __init__(self, db_path: str = None):
        self._config = get_config()
        self._db_path = db_path or self._config.audit.database_url
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self._db_path)
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seq INTEGER NOT NULL UNIQUE,
                ts TEXT NOT NULL,
                event_type TEXT NOT NULL,
                session_id TEXT,
                agent_framework TEXT,
                tool TEXT,
                arguments_hash TEXT,
                trust_score REAL,
                flags TEXT,
                decision TEXT,
                prev_hash TEXT NOT NULL,
                this_hash TEXT NOT NULL,
                payload_json TEXT
            )
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_session ON audit_log(session_id)
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_type ON audit_log(event_type)
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_ts ON audit_log(ts)
        """)
        
        conn.commit()
        conn.close()
    
    def _get_last_seq_and_hash(self) -> tuple:
        """Get the last sequence number and hash."""
        conn = sqlite3.connect(self._db_path)
        cur = conn.cursor()
        
        cur.execute("SELECT seq, this_hash FROM audit_log ORDER BY seq DESC LIMIT 1")
        row = cur.fetchone()
        
        conn.close()
        
        if row:
            return row[0], row[1]
        return 0, "GENESIS"
    
    def _compute_hash(
        self,
        prev_hash: str,
        seq: int,
        ts: str,
        event_type: str,
        session_id: str,
        arguments_hash: str,
        decision: str
    ) -> str:
        """Compute SHA-256 hash for record."""
        raw = f"{prev_hash}|{seq}|{ts}|{event_type}|{session_id}|{arguments_hash}|{decision}"
        return hashlib.sha256(raw.encode()).hexdigest()
    
    def write(
        self,
        event_type: str,
        session_id: str = None,
        agent_framework: str = None,
        tool: str = None,
        arguments: Dict[str, Any] = None,
        trust_score: float = None,
        flags: List[str] = None,
        decision: str = None,
        payload: Dict[str, Any] = None
    ) -> str:
        """Write a new audit record."""
        seq, prev_hash = self._get_last_seq_and_hash()
        
        ts = datetime.utcnow().isoformat() + "Z"
        new_seq = seq + 1
        
        arguments_hash = ""
        if arguments:
            args_str = json.dumps(arguments, sort_keys=True)
            arguments_hash = "sha256:" + hashlib.sha256(args_str.encode()).hexdigest()[:16]
        
        flags_str = json.dumps(flags) if flags else "[]"
        
        payload_json = json.dumps(payload, sort_keys=True) if payload else None
        
        this_hash = self._compute_hash(
            prev_hash, new_seq, ts, event_type,
            session_id or "", arguments_hash or "", decision or ""
        )
        
        conn = sqlite3.connect(self._db_path)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO audit_log (
                seq, ts, event_type, session_id, agent_framework, tool,
                arguments_hash, trust_score, flags, decision, prev_hash, this_hash, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            new_seq, ts, event_type, session_id, agent_framework, tool,
            arguments_hash, trust_score, flags_str, decision, prev_hash, this_hash, payload_json
        ))
        
        conn.commit()
        conn.close()
        
        return this_hash
    
    def verify_chain(self) -> bool:
        """Verify the integrity of the entire audit chain."""
        conn = sqlite3.connect(self._db_path)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT seq, ts, event_type, session_id, tool, arguments_hash, decision, prev_hash, this_hash
            FROM audit_log ORDER BY seq ASC
        """)
        
        rows = cur.fetchall()
        conn.close()
        
        prev_hash = "GENESIS"
        
        for row in rows:
            seq, ts, event_type, session_id, tool, arguments_hash, decision, stored_prev_hash, stored_this_hash = row
            
            if stored_prev_hash != prev_hash:
                print(f"Chain broken at seq={seq}: prev_hash mismatch")
                return False
            
            computed_hash = self._compute_hash(
                stored_prev_hash, seq, ts, event_type,
                session_id or "", arguments_hash or "", decision or ""
            )
            
            if computed_hash != stored_this_hash:
                print(f"Chain broken at seq={seq}: hash mismatch")
                return False
            
            prev_hash = stored_this_hash
        
        return True
    
    def query(
        self,
        session_id: str = None,
        event_type: str = None,
        tool: str = None,
        since: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query audit logs with filters."""
        conn = sqlite3.connect(self._db_path)
        cur = conn.cursor()
        
        conditions = []
        params = []
        
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        
        if tool:
            conditions.append("tool = ?")
            params.append(tool)
        
        if since:
            conditions.append("ts >= ?")
            params.append(since)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        cur.execute(f"""
            SELECT seq, ts, event_type, session_id, agent_framework, tool, 
                   arguments_hash, trust_score, flags, decision, this_hash
            FROM audit_log
            WHERE {where_clause}
            ORDER BY seq DESC
            LIMIT ?
        """, params + [limit])
        
        rows = cur.fetchall()
        conn.close()
        
        results = []
        
        for row in rows:
            results.append({
                "seq": row[0],
                "ts": row[1],
                "event_type": row[2],
                "session_id": row[3],
                "agent_framework": row[4],
                "tool": row[5],
                "arguments_hash": row[6],
                "trust_score": row[7],
                "flags": json.loads(row[8]) if row[8] else [],
                "decision": row[9],
                "this_hash": row[10][:16] + "..."
            })
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics."""
        conn = sqlite3.connect(self._db_path)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM audit_log")
        total = cur.fetchone()[0]
        
        cur.execute("""
            SELECT event_type, COUNT(*) 
            FROM audit_log 
            GROUP BY event_type
        """)
        event_counts = dict(cur.fetchall())
        
        cur.execute("""
            SELECT decision, COUNT(*) 
            FROM audit_log 
            WHERE decision IS NOT NULL
            GROUP BY decision
        """)
        decision_counts = dict(cur.fetchall())
        
        conn.close()
        
        return {
            "total_events": total,
            "event_counts": event_counts,
            "decision_counts": decision_counts
        }


_audit_store: Optional[AuditStore] = None


def get_audit_store(db_path: str = None) -> AuditStore:
    """Get or create the global audit store."""
    global _audit_store
    if _audit_store is None:
        _audit_store = AuditStore(db_path)
    return _audit_store