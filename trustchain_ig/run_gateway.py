import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
from gateway.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7070)