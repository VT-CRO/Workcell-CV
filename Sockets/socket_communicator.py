import socket
import time

class PrinterConnection:
    def __init__(self):
        self.camera_loop_path = "/tmp/camera_loop.sock"
        self.camera_ctrl_path = "/tmp/camera_ctrl.sock"
        self.camera_loop = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.camera_loop.connect(self.camera_loop_path)
        self.tag_id = None
        
    def wait_for_command(self):
        try:
            server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server_sock.connect(self.camera_ctrl_path)
            data = server_sock.recv(1024)
            server_sock.close()

            if data:
                print(data.decode())
                if "REQUEST" in data.decode():
                    tag_id = data.decode().split(" ")[1]
                    print(f"New command requested for {tag_id}")
                    self.tag_id = tag_id
                    return tag_id
        except Exception as e:
            print(f"Error connecting to camera control socket: {e}")
                
        return None
    
    def send_command(self, command):
        try:
            self.camera_loop.send(command.encode())
        except Exception as e:
            print(f"Error sending command: {e}")
        if command != "DONE":
            tag_id = self.wait_for_command()
        else:
            tag_id = None
        return tag_id