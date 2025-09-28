import websockets
import json
import asyncio

class CameraController:
    def __init__(self):
        self.websocket = None
        self.uri = "ws://192.168.0.100:7125/websocket"
        self.running = False
    
    async def connect(self):
        """Connect to Moonraker WebSocket and keep connection open"""
        try:
            self.websocket = await websockets.connect(self.uri)
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

    async def set_relative(self):
        """Set relative positioning mode"""
        if not self.websocket or not self.running:
            print("WebSocket not connected")
            return None
        
        try:
            mess = {"jsonrpc": "2.0", "method": "printer.gcode.script", "params": {"script": "G91"}, "id": 1}
            await self.websocket.send(json.dumps(mess))
            result = await self.websocket.recv()
            print(f"Set to relative positioning - Response: {result}")
            return result
        except Exception as e:
            print(f"Error setting relative mode: {e}")
            return None
    
    async def send_command(self, command):
        print("Sending command:", command)
        """Send a WASD command to move the camera"""
        if not self.websocket or not self.running:
            print("WebSocket not connected")
            return None
        
        if(command.lower == 'c'):
            return None
        # Map commands to G-code movements
        # L X+1, R X-1, U Y+1, D Y-1
        command_map = {
            "u": {"script": "G1 Y0.25", "description": "Move up"},
            "d": {"script": "G1 Y-0.25", "description": "Move down"}, 
            "l": {"script": "G1 X-0.25", "description": "Move left"},
            "r": {"script": "G1 X0.25", "description": "Move right"}
        }
        
        try:
            movement = command_map[command.lower()]
            mess = {"jsonrpc": "2.0", "method": "printer.gcode.script", "params": {"script": movement["script"]}, "id": 1}
            await self.websocket.send(json.dumps(mess))
            result = await self.websocket.recv()
            print(f"{movement['description']} - Response: {result}")
            return result
        except Exception as e:
            print(f"Error sending command: {e}")
            return None

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