import socket
import json
import os
import fcntl
import errno
import threading
import time


class KlipperComms:
    def __init__(self):
        self.command_socket_path = "/tmp/command_socket.sock"
        self.control_socket_path = "/tmp/control_socket.sock"
        self.command_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) # self.bind_sockets(self.command_socket_path)
        self.control_socket = self.bind_sockets(self.control_socket_path)
        self.tag_id = None
        self.needCommand = False
        self.startCommand = False
        self.thread = threading.Thread(target=self.start_control_socket)
        self.thread.start()

    def bind_sockets(self, path):
        if os.path.exists(path):
            os.unlink(path)
        if path == self.command_socket_path:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        elif path == self.control_socket_path:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        else:
            raise ValueError(f"Invalid socket path: {path}")
        s.bind(path)
        os.chmod(path, 0o666)
        # fcntl.fcntl(s, fcntl.F_SETFL, os.O_NONBLOCK)
        return s

    def start_control_socket(self):
        self.control_socket.listen(1)
        while True:
            print("Waiting for control socket connection")
            conn, addr = self.control_socket.accept()
            data = conn.recv(1024).decode()
            if data.startswith("START") and not self.startCommand:
                self.tag_id = int(data.split(" ")[1])
                self.needCommand = True
                self.startCommand = True
            elif data.startswith("REQUEST") and self.startCommand:
                self.needCommand = True
            conn.close()
                
    def sendCommand(self, command):
        while not self.needCommand:
            time.sleep(0.1)
        if command == "DONE":
            self.startCommand = False
            self.endRunning()
        self.command_socket.sendto(command.encode(),self.command_socket_path)
        print(f"Sent command: {command}")
        self.needCommand = False
                
    def currentlyRunning(self):
        return self.tag_id is not None
    
    def get_tag_id(self):
        return self.tag_id
    
    def endRunning(self):
        self.tag_id = None
    
    def get_needCommand(self):
        return self.needCommand
    
    def requestCommand(self):
        self.needCommand = False

    # def start_command_socket(self):
    #     # For SOCK_DGRAM, we don't use listen/accept
    #     # Instead, we recv data directly
    #     data, addr = self.command_socket.recvfrom(1024)
    #     print(f"Received command: {data.decode()}")
    #     self.command_socket.close()