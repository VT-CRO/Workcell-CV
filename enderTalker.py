import websockets
import json
import asyncio
import itertools

class CameraController:
    def __init__(self):
        self.websocket = None
        self.uri = "ws://192.168.0.100:7125/websocket"
        self.running = False
        self._id_iter = itertools.count(1)

    async def connect(self):
        """Connect to Moonraker WebSocket and keep connection open"""
        try:
            self.websocket = await websockets.connect(self.uri)
            self._id_iter = itertools.count(1)
            print("Connected to Moonraker websocket - connection will stay open")
            self.running = True
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False

    async def disconnect(self):
        """Close the WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            print("Connection closed")
            self.running = False

    async def _await_response(self, request_id):
        """Wait for the Moonraker response that matches the request id"""
        while True:
            raw_message = await self.websocket.recv()
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError:
                print(f"Received non-JSON message: {raw_message}")
                continue

            if message.get("id") == request_id:
                if "error" in message:
                    raise RuntimeError(message["error"])
                return message

            method = message.get("method")
            if method == "notify_gcode_response":
                params = message.get("params") or []
                if params:
                    print(f"Klipper: {params[0]}")
                continue

            print(f"Ignoring unsolicited message: {message}")

    async def _send_gcode(self, script, description=None):
        if not self.websocket or not self.running:
            print("WebSocket not connected")
            return None

        request_id = next(self._id_iter)
        payload = {
            "jsonrpc": "2.0",
            "method": "printer.gcode.script",
            "params": {"script": script},
            "id": request_id,
        }

        try:
            await self.websocket.send(json.dumps(payload))
            response = await self._await_response(request_id)
            response_text = json.dumps(response, separators=(",", ":"))
            if description:
                print(f"{description} - Response: {response_text}")
            else:
                print(f"Response: {response_text}")
            return response
        except RuntimeError as err:
            print(f"G-code execution failed: {err}")
        except Exception as exc:
            print(f"Error communicating with Moonraker: {exc}")
        return None

    async def set_relative(self):
        """Set relative positioning mode"""
        return await self._send_gcode("G91", "Set to relative positioning")

    async def send_command(self, command, distMultiplier=1.0):
        print(f"Sending command: {command} with multiplier: {distMultiplier}")
        """Send a WASD command to move the camera"""
        if not self.websocket or not self.running:
            print("WebSocket not connected")
            return None

        if command.lower() == "c":
            return None

        base_distance = 1
        move_distance = base_distance * distMultiplier
        distance_str = f"{move_distance:.4f}"

        # Map commands to G-code movements
        # L X+1, R X-1, U Y+1, D Y-1
        command_map = {
            "u": {"script": f"G1 Y{distance_str}", "description": "Move up"},
            "d": {"script": f"G1 Y-{distance_str}", "description": "Move down"},
            "l": {"script": f"G1 X-{distance_str}", "description": "Move left"},
            "r": {"script": f"G1 X{distance_str}", "description": "Move right"},
        }

        movement = command_map.get(command.lower())
        if not movement:
            print(f"Unsupported command: {command}")
            return None

        script = f"{movement['script']}\nM400"
        return await self._send_gcode(script, movement["description"])

# Global camera controller instance
camera = CameraController()

async def camera_control():
    """Main function to run camera control with interactive input"""
    if not await camera.connect():
        return

    print("Commands: w=up, s=down, a=left, d=right, q=quit")

    while camera.running:
        direction = input("Enter direction (w=up, s=down, a=left, d=right, q=quit): ")

        if direction.lower() == "q":
            print("Closing connection...")
            break
        else:
            await camera.send_command(direction)

    await camera.disconnect()

# Function to be called by other parts of your program
async def move_camera(command):
    """Public function to send camera movement commands from other functions"""
    return await camera.send_command(command)

# Run the camera control
# L X+1
# R X-1
# U Y+1
# D Y-1
if __name__ == "__main__":
    asyncio.run(camera_control())
