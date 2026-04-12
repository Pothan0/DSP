import os

DB_FILE = "trustchain.db"
MESSAGE_QUEUE_TABLE = "message_queue"
AUDIT_TABLE = "audit_log"

TRUST_THRESHOLD = 0.5
ANOMALY_SIMILARITY_THRESHOLD = 0.35
ANOMALY_WINDOW_SIZE = 20

CAPABILITY_TOKEN_TTL = 300  # 5 minutes in seconds

HITL_RISK_THRESHOLD = 0.7
IRREVERSIBLE_WEIGHTS = {
    "file_write": 1.0,
    "http_request": 1.0,
    "memory_write": 1.0,
    "read": 0.3,
    "default": 0.5
}

HOP_DECAY = 0.1
ANOMALY_DECAY = 0.15
PROVENANCE_BONUS = 0.1
HOP_PENALTY_THRESHOLD = 2

LLM_MODEL = "llama3.2:1b"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

WEBSOCKET_HOST = "0.0.0.0"
WEBSOCKET_PORT = 8765

LOG_LEVEL = "INFO"