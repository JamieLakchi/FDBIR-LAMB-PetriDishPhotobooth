import io
import socket

from typing import Optional, Callable
from PIL import Image

from src.connections import Connection, RequestType, rtob, PROTOCOL_PORT
from src.logs import ERROR
from src.exceptions import CaptureFailed

class ImagerClientConnection:
    def __init__(self, log: Callable[[str, str], None]) -> None:
        """
        Constructs client side of connection

        logger: logger that is being used by frontend (same logfile)
        """
        self.__log = log
        self.hostname : Optional[str] = None
        self.connection : Optional[Connection] = None

    def discover(self, hostname: str) -> Optional[str]:
        """
        Looks for IP of host using hostname and mDNS

        hostname: string with canonical hostname
        """
        
        try:
            ip = socket.gethostbyname(hostname)
            self.hostname = hostname
        except:
            self.__log(ERROR, f"could not find {hostname} on network")
            return

        return ip
    
    def connect(self, ip: str) -> Optional[str]:
        """
        Connects to ip at protocol port, returns ip on success, else None

        ip: string with IPv4 address
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ip, PROTOCOL_PORT))
            sock.settimeout(120)
            self.connection = Connection(sock)
        except:
            self.__log(ERROR, f"could not connect to {ip}@{PROTOCOL_PORT}")
            return
        
        return ip
    
    def __close(self) -> None:
        if self.connection is not None:
            self.connection.close()

        self.connection = None

    def check_connection(self) -> Optional[Connection]:
        """
        Checks if the connection is still up, raises NoConnectionAvailble if not
        """
        if self.connection is None:
            self.__log(ERROR, "No connection available")
            return
        
        try:
            self.connection.send_fmsg(rtob(RequestType.CHECK_CONNECTED))
            msg = self.connection.recv_fmsg()
        except:
            self.__log(ERROR, "No connection available")
            self.__close()
            return
        
        return self.connection
    
    def capture(self, preview = True) -> Optional[Image.Image]:
        """Sends capture request, preview = True captures preview, False captures main"""
        connection = self.check_connection()

        if connection is None:
            return

        connection.send_fmsg(rtob(RequestType.CAPTURE_PREVIEW if preview else RequestType.CAPTURE_MAIN))
        
        try:
            preview_bytes = connection.recv_fmsg()

            if preview_bytes == b"":
                raise CaptureFailed()

            preview_image = Image.open(io.BytesIO(preview_bytes))

        except CaptureFailed as e:
            self.__log(ERROR, "Capture failed")
            return
        except:
            self.__log(ERROR, "No connection available")
            self.__close()
            return

        return preview_image
    
    def power_off(self) -> None:
        """Tries to send power off signal (may fail), and terminates connection"""
        
        try:
            connection = self.check_connection()
            if not connection is None:
                connection.send_fmsg(rtob(RequestType.POWER_OFF))
        finally:
            self.__close()

    def __str__(self) -> str:
        """String representation of the object"""
        if self.hostname is None or self.connection is None:
            return "<NotConnected>"

        sockname = self.connection.sock.getpeername()        

        return f"{self.hostname}@{sockname[0]}:{sockname[1]}"