import asyncio
import json
import itertools
from typing import Optional

import websockets


class CameraController:
    """Manage a persistent Moonraker WebSocket connection and send raw G-code."""

    def __init__(self) -> None:
        self.uri = "ws://192.168.0.100:7125/websocket"
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self._id_iter = itertools.count(1)

    async def connect(self) -> bool:
        """Connect to Moonraker and keep the socket open for future commands."""
        try:
            self.websocket = await websockets.connect(self.uri)
            self._id_iter = itertools.count(1)
            self.running = True
            print("Connected to Moonraker websocket - connection will stay open")
            return True
        except Exception as exc:
            print(f"Failed to connect: {exc}")
            self.running = False
            self.websocket = None
            return False

    async def disconnect(self) -> None:
        """Close the existing WebSocket connection."""
        if self.websocket is not None:
            await self.websocket.close()
        self.running = False
        self.websocket = None
        print("Connection closed")

    async def send_gcode(self, gcode: str) -> Optional[dict]:
        """Send a block of raw G-code over the active connection."""
        if not gcode:
            print("No G-code provided")
            return None
        if not self.websocket or not self.running:
            print("WebSocket not connected")
            return None

        request_id = next(self._id_iter)
        payload = {
            "jsonrpc": "2.0",
            "method": "printer.gcode.script",
            "params": {"script": gcode},
            "id": request_id,
        }

        try:
            await self.websocket.send(json.dumps(payload))
            response = await self._await_response(request_id)
            print("Command executed")
            return response
        except RuntimeError as err:
            print(f"G-code execution failed: {err}")
        except Exception as exc:
            print(f"Error communicating with Moonraker: {exc}")
        return None

    async def _await_response(self, request_id: int) -> dict:
        """Listen until Moonraker replies to the provided request id."""
        assert self.websocket is not None
        while True:
            raw_message = await self.websocket.recv()
            message = json.loads(raw_message)

            if message.get("id") == request_id:
                if "error" in message:
                    raise RuntimeError(message["error"])
                return message

            method = message.get("method")
            if method == "notify_gcode_response":
                continue


def main() -> None:
    async def _run() -> None:
        controller = CameraController()
        if not await controller.connect():
            return
        try:
            while True:
                user_input = input("Enter G-code (q to quit): ").strip()
                if not user_input or user_input.lower() in {"q", "quit"}:
                    break
                await controller.send_gcode(user_input)
        finally:
            await controller.disconnect()

    asyncio.run(_run())


if __name__ == "__main__":
    main()


camera = CameraController()
