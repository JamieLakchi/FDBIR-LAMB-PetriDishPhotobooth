import socket
import struct
import threading
from PIL import Image
import io
import time

class PhotoboothProtocolClient:
    def __init__(self):
        self.sock = None
        self.connected = False
        self.keepalive_thread = None
        self.keepalive_active = False
        self.on_lost_connection = None
        self.last_operation_time = 0
        
    def isConnected(self):
        return self.connected

    def onLostConnection(self, func):
        self.onLostConnection = func

    def connect(self, ip, port):
        """Open TCP connection; returns true on success, false on failure"""
        try:
            self.close()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)  # 10 second timeout
            self.sock.connect((ip, port))
            self.connected = True
            
            # Start keep-alive thread
            self.keepalive_active = True
            self.keepalive_thread = threading.Thread(target=self._keepalive_loop)
            self.keepalive_thread.daemon = True
            self.keepalive_thread.start()
            
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            self.close()
            return False

    def _keepalive_loop(self):
        """Background thread to send keep-alive messages"""

        while self.keepalive_active and self.connected:
            if time.time() - self.last_operation_time >= 5:
                try:
                    # Send keep-alive command
                    cmd_data = b"KEEPALIVE"
                    self.sock.sendall(struct.pack('!I', len(cmd_data)))
                    self.sock.sendall(cmd_data)
                    
                    # Wait for keep-alive response
                    header_size = struct.calcsize('!I')
                    header = self.sock.recv(header_size)
                    if len(header) != header_size:
                        raise Exception("Invalid keep-alive response")
                        
                    response_size = struct.unpack('!I', header)[0]
                    if response_size > 0:
                        # Read and discard the response
                        self.sock.recv(response_size)
                        
                except Exception as e:
                    print(f"Keep-alive error: {e}")
                    self.connected = False
                    self.close()
                    if self.on_lost_connection:
                        self.on_lost_connection()
                    break
                    
            time.sleep(1)  # Check every second

    def _send_command(self, command):
        """Helper method to send a command and receive response"""
        try:
            # Update last operation time
            self.last_operation_time = time.time()
            
            # Send command length and command
            cmd_data = command.encode('utf-8')
            self.sock.sendall(struct.pack('!I', len(cmd_data)))
            self.sock.sendall(cmd_data)
            
            # Receive response header
            header_size = struct.calcsize('!I')
            header = self.sock.recv(header_size)
            if len(header) != header_size:
                return None
                
            response_size = struct.unpack('!I', header)[0]
            
            # Receive response data
            response_data = b''
            while len(response_data) < response_size:
                chunk = self.sock.recv(min(4096, response_size - len(response_data)))
                if not chunk:
                    break
                response_data += chunk
                
            return response_data
            
        except Exception as e:
            print(f"Communication error: {e}")
            self.connected = False
            return None

    def getMain(self):
        """Request and receive main high-resolution image"""
        response = self._send_command("GET_MAIN")
        if response:
            try:
                return Image.open(io.BytesIO(response))
            except Exception as e:
                print(f"Error decoding main image: {e}")
        return None

    def getPreview(self):
        """Request and receive preview low-resolution image"""
        response = self._send_command("GET_PREVIEW")
        if response:
            try:
                return Image.open(io.BytesIO(response))
            except Exception as e:
                print(f"Error decoding preview image: {e}")
        return None

    def close(self):
        """Closes TCP connection if one exists"""
        self.keepalive_active = False
        if self.keepalive_thread and self.keepalive_thread.is_alive():
            self.keepalive_thread.join(timeout=1.0)
            
        if self.sock is not None:
            try:
                self.sock.close()
            except:
                pass
            finally:
                self.sock = None
                self.connected = False