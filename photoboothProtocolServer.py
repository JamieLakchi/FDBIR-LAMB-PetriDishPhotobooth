import socket
import struct
import threading
from PIL import Image
import io
import time

class PhotoboothProtocolServer:
    def __init__(self, host='0.0.0.0', port=8888):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.client_handler = None
        
    def start(self):
        """Start the server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen()
            self.running = True
            
            print(f"Server started on {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    print(f"Client connected: {client_address}")
                    
                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"Server error: {e}")
                        
        except Exception as e:
            print(f"Failed to start server: {e}")
            
    def _handle_client(self, client_socket, client_address):
        """Handle client communication"""
        try:
            client_socket.settimeout(30)  # 30 second timeout
            
            while True:
                # Read command length
                header_size = struct.calcsize('!I')
                header = client_socket.recv(header_size)
                if not header:
                    break
                    
                cmd_size = struct.unpack('!I', header)[0]
                
                # Read command
                cmd_data = b''
                while len(cmd_data) < cmd_size:
                    chunk = client_socket.recv(min(4096, cmd_size - len(cmd_data)))
                    if not chunk:
                        break
                    cmd_data += chunk
                    
                command = cmd_data.decode('utf-8')
                print(f"Received command: {command}")
                
                # Process command
                if command == "GET_MAIN":
                    image_data = self._capture_main_image()
                elif command == "GET_PREVIEW":
                    image_data = self._capture_preview_image()
                elif command == "KEEPALIVE":
                    # Respond to keep-alive with empty message
                    image_data = b''
                else:
                    image_data = None
                
                # Send response
                if image_data is not None:
                    # Send response size first
                    client_socket.sendall(struct.pack('!I', len(image_data)))
                    # Send response data
                    if len(image_data) > 0:
                        client_socket.sendall(image_data)
                else:
                    # Send error response for invalid commands
                    error_msg = b"Invalid command"
                    client_socket.sendall(struct.pack('!I', len(error_msg)))
                    client_socket.sendall(error_msg)
                    
        except socket.timeout:
            print(f"Client timeout: {client_address}")
        except Exception as e:
            print(f"Client handling error: {e}")
        finally:
            client_socket.close()
            print(f"Client disconnected: {client_address}")
    
    def _capture_main_image(self):
        """Capture and return main high-resolution image bytes"""
        # This is where you'll integrate with picamera2
        try:
            img = Image.new('RGB', (1920, 1080), color='red')
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=95)
            return img_byte_arr.getvalue()
        except Exception as e:
            print(f"Error capturing main image: {e}")
            return None
    
    def _capture_preview_image(self):
        """Capture and return preview low-resolution image bytes"""
        # This is where you'll integrate with picamera2
        try:
            img = Image.new('RGB', (640, 480), color='blue')
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=80)
            return img_byte_arr.getvalue()
        except Exception as e:
            print(f"Error capturing preview image: {e}")
            return None
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("Server stopped")