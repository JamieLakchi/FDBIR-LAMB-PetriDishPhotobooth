import socket
import struct

from typing import Optional
from pathlib import Path
from enum import Enum

from src.exceptions import SocketReceivedBytesEmpty

PROTOCOL_PORT = 8888

HEADER_FRMT = "!Q"
HEADER_SIZE = struct.calcsize(HEADER_FRMT)

class RequestType(Enum):
    CHECK_CONNECTED = 0
    CAPTURE_MAIN = 1
    CAPTURE_PREVIEW = 2
    POWER_OFF = 3

def rtob(req: RequestType) -> bytes:
    """RequestType object to bytes"""
    return req.value.to_bytes(1, 'little')

def format_address_tuple(address_tuple: tuple) -> str:
    """Formats entries from tuple as tuple[0]:tuple[1]"""
    return f"{address_tuple[0]}:{address_tuple[1]}"

class Connection:
    def __init__(self, sock: socket.socket) -> None:
        """Wrapper for sockets"""
        self.sock = sock

    def recvb(self, n: int) -> Optional[bytes]:
        """Attempts to receive n bytes from socket, None on failure"""
        data = b''
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            
            if not chunk:
                return None

            data += chunk
        return data

    def send(self, msg: bytes) -> bool:
        """Attempts to send msg, returns True on success"""
        try:
            self.sock.sendall(msg)
        except:
            return False
        return True

    def send_fmsg(self, msg: bytes) -> bool:
        """Sends formatted message"""
        req_len = len(msg)
        message = struct.pack(HEADER_FRMT, req_len) + msg
        return self.send(message)
    
    def recv_fmsg(self) -> bytes:
        """Receive a message with a header and body"""
        incomming_size_header = self.recvb(HEADER_SIZE)

        if incomming_size_header is None:
            raise SocketReceivedBytesEmpty()
        
        incomming_size = struct.unpack(HEADER_FRMT, incomming_size_header)[0]
        
        incomming_msg_body = self.recvb(incomming_size)

        if incomming_msg_body is None:
            raise SocketReceivedBytesEmpty()
        
        return incomming_msg_body
    
    def close(self) -> None:
        """Closes the socket"""
        self.sock.close()

    def send_file(self, fname: Path) -> bool:
        """Sends given file through socket"""

        buffer = b'' 
        with fname.open('rb') as file:
            buffer = file.read()
        
        header = struct.pack(HEADER_FRMT, len(buffer))

        h = self.send(header)
        b = self.send(buffer)
        return h and b