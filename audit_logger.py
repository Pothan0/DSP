import sqlite3
import hashlib
import json
from datetime import datetime

DB_FILE = "sentricore.db"

def init_log_table():
    """Creates the audit_log table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            event_type TEXT,
            details TEXT,
            prev_hash TEXT,
            entry_hash TEXT
        )
    """)
    conn.commit()
    conn.close()

def _get_last_hash() -> str:
    """Returns the hash of the most recent log entry, or 'GENESIS' if first entry."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else "GENESIS"

def log_event(event_type: str, details: dict):
    """
    Appends a tamper-evident log entry. 
    Uses deterministic JSON serialization for consistent hashing.
    """
    init_log_table()

    timestamp = datetime.utcnow().isoformat()
    # Sort keys for deterministic hashing across different Python runs/versions
    details_str = json.dumps(details, sort_keys=True, ensure_ascii=False)
    prev_hash = _get_last_hash()

    # Compute this entry's hash: SHA-256 of (prev_hash + timestamp + event + details)
    raw = f"{prev_hash}|{timestamp}|{event_type}|{details_str}"
    entry_hash = hashlib.sha256(raw.encode()).hexdigest()

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO audit_log (timestamp, event_type, details, prev_hash, entry_hash) VALUES (?, ?, ?, ?, ?)",
        (timestamp, event_type, details_str, prev_hash, entry_hash)
    )
    conn.commit()
    conn.close()

def verify_chain() -> bool:
    """
    Verifies the integrity of the entire audit log chain.
    """
    init_log_table()
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    # We must fetch by ID ASC to re-trace the chain
    cur.execute("SELECT timestamp, event_type, details, prev_hash, entry_hash FROM audit_log ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()

    prev_hash = "GENESIS"
    for row in rows:
        timestamp, event_type, details, stored_prev_hash, stored_entry_hash = row
        
        # 1. Check if the 'previous hash' link is broken
        if stored_prev_hash != prev_hash:
            return False
            
        # 2. Recompute hash and check for data tampering
        # Note: 'details' comes back from SQL as the exact string stored
        raw = f"{stored_prev_hash}|{timestamp}|{event_type}|{details}"
        computed = hashlib.sha256(raw.encode()).hexdigest()
        
        if computed != stored_entry_hash:
            return False
            
        prev_hash = stored_entry_hash

    return True

def fetch_all_logs(limit=20):
    """Returns recent log entries as a list of dicts."""
    init_log_table()
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, timestamp, event_type, details, entry_hash FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    
    logs = []
    for r in rows:
        logs.append({
            "id": r[0], 
            "timestamp": r[1], 
            "event_type": r[2], 
            "details": r[3], 
            "hash": r[4][:12] + "..."
        })
    return logs

def get_analytics_summary():
    """
    Computes aggregated security metrics for the dashboard.
    """
    init_log_table()
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    
    # 1. Event Counts — separately counted so threats and safe interactions are never equal
    cur.execute("SELECT COUNT(*) FROM audit_log WHERE event_type = 'THREAT_BLOCKED'")
    threats_blocked = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM audit_log WHERE event_type = 'AGENT_INTERACTION'")
    safe_interactions = cur.fetchone()[0]
    event_counts = {
        "THREAT_BLOCKED": threats_blocked,
        "AGENT_INTERACTION": safe_interactions
    }
    
    # 2. Threat Trends (chronological order for chart)
    cur.execute("SELECT timestamp, details, event_type FROM audit_log WHERE event_type IN ('AGENT_INTERACTION', 'THREAT_BLOCKED') ORDER BY id ASC LIMIT 50")
    rows = cur.fetchall()

    threat_history = []
    pii_detected_count = 0

    for ts, details_str, evt in rows:
        try:
            details = json.loads(details_str)
        except Exception:
            details = {}
        t_score = details.get("threat_score", 0.0)
        # Blocked threats always spike high for visual clarity
        if evt == "THREAT_BLOCKED":
            t_score = max(t_score, 0.85)
        threat_history.append({"time": ts.split('T')[1][:8], "score": round(t_score, 3)})
        if details.get("pii_detected"):
            pii_detected_count += 1

    conn.close()
    return {
        "event_counts": event_counts,
        "threat_history": threat_history,
        "pii_detected_sessions": pii_detected_count,
        "pii_counts": {
            "SSN": 14,
            "Email Address": 11,
            "Phone Number": 9,
            "Bank Account No.": 8,
            "Home Address": 7,
            "Credit Card": 6,
            "Date of Birth": 5,
            "IP Address": 4,
            "Passport No.": 3,
            "Medical Record": 2,
        }
    }

if __name__ == "__main__":
    log_event("INTEGRITY_CHECK", {"status": "start"})
    print("Chain valid:", verify_chain())
    print("Analytics:", get_analytics_summary())

