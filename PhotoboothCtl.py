import socket
import struct
import logging
import threading
import subprocess
import io
import os

from typing import Optional

HEADER_FRMT = "!Q"
HEADER_SIZE = struct.calcsize(HEADER_FRMT)

def _recvb(sock: socket.socket, n: int) -> Optional[bytes]:
    "Attempts to receive n bytes from socket, None on failure"
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        
        if not chunk:
            return None

        data += chunk
    return data

def _send(sock: socket.socket, msg: bytes) -> bool:
    """Attempts to send msg, returns True on success"""
    try:
        sock.sendall(msg)
    except:
        return False
    return True

def _send_req(sock: socket.socket, req: str) -> bool:
    as_bytes = req.encode("utf-8")
    req_len = len(as_bytes)
    message = struct.pack(HEADER_FRMT, req_len) + as_bytes
    return _send(sock, message)

class PhotoboothControl:
    def __init__(self, gui):
        self.gui = gui
        self.sock: Optional[socket.socket] = None

    def _close(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def _recvb_and_log(self, n: int, max_chunk_size: int=8192) -> Optional[bytes]:
        if self.sock is None:
            return None
        
        data = b''
        chunk_size = min(max_chunk_size, n)
        self.gui.log_info("receiving at 8192 bytes per chunk")

        while len(data):
            chunk = self.sock.recv(chunk_size)

            if not chunk:
                return None
            
            data += chunk

            self.gui.log_info(f"[{(len(data)*100)//n}%] downloading...")

        return chunk

    def discover(self):
        """Attempts to establish socket connection"""
        self._close()
        hostname = self.gui.get_hostname()

        if hostname is None:
            self.gui.log_error("no hostname given")
            return
        
        self.gui.log_info(f"looking for {hostname}.local")

        try:
            ip = socket.gethostbyname(hostname)
            self.gui.log_info(f"found {hostname} at {ip}")
        except:
            self.gui.log_error(f"failed to find {hostname}")
            return
        
        self.gui.log_info(f"attempting connection to {ip}:8888")

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((ip, 8888))
            self.gui.log_info(f"connected to {ip}:8888")
        except:
            self.gui.log_error(f"failed to connect to {ip}:8888")
            self._close()

    def capture_main(self):
        dirname = self.gui.get_dirname()
        if dirname is None:
            self.gui.log_error("no directory selected")
            return
        
        if self.sock is None:
            self.gui.log_error("no connection to pi")
            return

        self.gui.log_info("attempting to capture main")

        if not _send_req(self.sock, "CAPTURE_MAIN"):
            self.log_error("failed to request main (connection might be lost)")
            return
        
        main_len = struct.calcsize("!I")

    def capture_preview(self):
        pass

    def power_off(self):
        pass

def _send_file(sock: socket.socket, fname: str):
    """Sends given file through socket"""
    buffer = io.BytesIO()

    with open(fname, 'rb') as file:
        file.readinto(fname)
    
    header = struct.pack(HEADER_FRMT, len(buffer))

    _send(sock, header)
    _send(sock, buffer)

class PhotoboothControlServer:
    def __init__(self):
        self.sock: Optional[socket.socket] = None
        self.logger = logging.getLogger("BoothCTLServer")

    def start(self, ip, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()

        self.running = True
            
        self.logger.info(f"Server started on {self.host}:{self.port}")
        
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                self.logger.info(f"Client connected: {client_address}")
                
                # Handle client in a separate thread
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                client_thread.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"Server error: {e}")

    def _handle_client(self, client_socket, client_address):
        try:
            while True:
                req_header = _recvb(client_socket, HEADER_SIZE)

                if not req_header:
                    self.logger.error(f"Failed to read request header")

                req_size = struct.unpack(HEADER_FRMT, req_header)[0]

                req = _recvb(client_socket, req_size).decode("utf-8")

                if req == "CAPTURE_MAIN":
                    self._capture_main(client_socket)
                elif req == "CAPTURE_PREVIEW":
                    self._capture_preview(client_socket)
                elif req == "POWER_OFF":
                    subprocess.run(["sudo", "shutdown", "now"])

        except Exception as e:
            self.logger.error(f"Client handling error: {e}")
        finally:
            client_socket.close()
            self.logger.info(f"Client disconnected: {client_address}")

    def _capture_main(self, sock):
        subprocess.run(["rpicam-still",
                            "-o", "/tmp/img.jpg",
                            "--width", "8000",
                            "--height", "6000",
                            "-n", "--immediate", "--autofocus-on-capture",
                            "--denoise", "cdn_off"])
        
        _send_file(sock, "/tmp/img.jpg")

    def _capture_preview(self, sock):
        subprocess.run(["rpicam-still",
                            "-o", "/tmp/img.jpg",
                            "--width", "2312",
                            "--height", "1736",
                            "-n", "--immediate", "--autofocus-on-capture",
                            "--denoise", "cdn_off"])
        
        _send_file(sock, "/tmp/img.jpg")

    def stop(self):
        """Stop the server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("Server stopped")

                
