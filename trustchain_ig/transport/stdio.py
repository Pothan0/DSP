import asyncio
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class StdioProxyTransport:
    def __init__(self, command: str, args: list[str]):
        self.command = command
        self.args = args
        self.process: Optional[asyncio.subprocess.Process] = None

    async def start(self):
        """Starts the subprocess and connects to its stdin and stdout."""
        logger.info(f"Starting subprocess: {self.command} {' '.join(self.args)}")
        self.process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    async def send_message(self, message: Dict[str, Any]):
        """Sends a JSON-RPC message to the subprocess stdin."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Subprocess not running or stdin not available")
        
        message_bytes = json.dumps(message).encode("utf-8") + b"\n"
        self.process.stdin.write(message_bytes)
        await self.process.stdin.drain()

    async def read_message(self) -> Optional[Dict[str, Any]]:
        """Reads a JSON-RPC message from the subprocess stdout non-blockingly."""
        if not self.process or not self.process.stdout:
            raise RuntimeError("Subprocess not running or stdout not available")
        
        try:
            line = await self.process.stdout.readline()
            if not line:
                return None
            return json.loads(line.decode("utf-8").strip())
        except Exception as e:
            logger.error(f"Error reading from subprocess: {e}")
            return None

    async def stop(self):
        """Stops the subprocess."""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.process = None

if __name__ == "__main__":
    async def _test():
        # A quick smoke test to verify it runs without hanging
        import sys
        transport = StdioProxyTransport(sys.executable, ["-c", "import sys; print('{\"hello\": \"world\"}'); sys.stdout.flush()"])
        await transport.start()
        msg = await transport.read_message()
        print("Received:", msg)
        await transport.stop()

    asyncio.run(_test())
