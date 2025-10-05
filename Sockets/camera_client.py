#!/usr/bin/env python3

# Talks to the camera_loop.sock socket

"""
Simple client to send data to the camera_loop.sock socket
"""

import socket
import time
import sys

def send_to_camera_socket(message, socket_path="/tmp/camera_loop.sock"):
    """Send a message to the camera loop socket"""
    try:
        # Create a Unix domain socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        
        # Send the message
        sock.sendto(message.encode(), socket_path)
        print(f"Sent: {message}")
        
        # Close the socket
        sock.close()
        
    except FileNotFoundError:
        print(f"Error: Socket {socket_path} not found. Make sure the server is running.")
    except Exception as e:
        print(f"Error sending message: {e}")

def main():
    if len(sys.argv) > 1:
        # Send command line argument
        message = " ".join(sys.argv[1:])
        send_to_camera_socket(message)
    else:
        # Interactive mode
        print("Camera Socket Client")
        print("Type messages to send (or 'quit' to exit):")
        
        while True:
            try:
                message = input("> ")
                if message.lower() in ['quit', 'exit', 'q']:
                    break
                if message.strip():
                    send_to_camera_socket(message)
            except KeyboardInterrupt:
                print("\nExiting...")
                break

if __name__ == "__main__":
    main()
