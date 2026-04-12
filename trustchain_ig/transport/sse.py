import asyncio
import json
import logging
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class SseProxyTransport:
    """
    An HTTP client transport that connects to downstream MCP servers via Server-Sent Events (SSE).
    """
    def __init__(self, sse_url: str):
        self.sse_url = sse_url
        self.message_url: Optional[str] = None
        self.client: Optional[httpx.AsyncClient] = None
        self.queue: asyncio.Queue = asyncio.Queue()
        self._listen_task: Optional[asyncio.Task] = None

    async def start(self):
        """Starts the SSE client connection and listens for events."""
        self.client = httpx.AsyncClient(timeout=None)
        
        async def listen():
            try:
                # Basic manual SSE parser for the client side
                async with self.client.stream("GET", self.sse_url) as response:
                    buffer = ""
                    async for chunk in response.aiter_text():
                        buffer += chunk
                        while "\n\n" in buffer:
                            event_text, buffer = buffer.split("\n\n", 1)
                            await self._parse_event(event_text)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error reading SSE stream: {e}")
                
        self._listen_task = asyncio.create_task(listen())

    async def _parse_event(self, event_text: str):
        event_type = "message"
        data = ""
        for line in event_text.splitlines():
            if line.startswith("event:"):
                event_type = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data += line.split(":", 1)[1].strip()
        
        if event_type == "endpoint" and data:
            # Construct the absolute message URL
            self.message_url = data if data.startswith("http") else str(httpx.URL(self.sse_url).join(data))
        elif event_type == "message" and data:
            try:
                msg = json.loads(data)
                await self.queue.put(msg)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode message: {data}")

    async def send_message(self, message: Dict[str, Any]):
        """Sends a JSON-RPC message via HTTP POST."""
        if not self.client:
            raise RuntimeError("Transport not started")
        
        post_url = self.message_url or self.sse_url.replace("/sse", "/message")
        
        response = await self.client.post(post_url, json=message)
        response.raise_for_status()

    async def read_message(self) -> Optional[Dict[str, Any]]:
        """Reads a JSON-RPC message from the queue."""
        return await self.queue.get()

    async def stop(self):
        """Stops the transport."""
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        if self.client:
            await self.client.aclose()
            self.client = None
