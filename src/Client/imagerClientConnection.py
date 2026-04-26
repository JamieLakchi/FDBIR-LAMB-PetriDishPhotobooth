import io
import socket

from typing import Optional
from PIL import Image

from src.connections import Connection, RequestType, rtob, PROTOCOL_PORT
from src.logs import Logger, INFO, WARN, ERROR
from src.exceptions import HostNotFound, ConnectionRefused, NoConnectionAvailable, CaptureFailed

class ImagerClientConnection:
    def __init__(self, logger: Logger) -> None:
        """
        Constructs client side of connection

        logger: logger that is being used by frontend (same logfile)
        """
        self.logger = logger
        self.hostname : Optional[str] = None
        self.connection : Optional[Connection] = None

    def __log(self, type: str, msg: str):
         """
         Creates log with name of class attached
         
         type: type of log
         msg: message to log
         """
         self.logger.log(type, msg, "ImagerClientConnection")

    def discover(self, hostname: str) -> str:
        """
        Looks for IP of host using hostname and mDNS

        hostname: string with canonical hostname
        """
        self.__log(INFO, f"looking for IP of {hostname}")
        
        try:
            ip = socket.gethostbyname(hostname)
            self.__log(INFO, f"found {hostname}@{ip}")
            self.hostname = hostname
        except:
            self.__log(ERROR, f"could not find {hostname} on network")
            raise HostNotFound(f"could not find {hostname} on network")

        return ip
    
    def connect(self, ip: str) -> None:
        """
        Connects to ip at protocol port

        ip: string with IPv4 address
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ip, PROTOCOL_PORT))
            sock.settimeout(120)
            self.connection = Connection(sock)
        except:
            self.__log(ERROR, f"could not connect to {ip}@{PROTOCOL_PORT}")
            raise ConnectionRefused(f"could not connect to {ip}@{PROTOCOL_PORT}")
        
    def __close(self) -> None:
        if self.connection is not None:
            self.connection.close()

        self.connection = None

    def check_connection(self) -> Connection:
        """
        Checks if the connection is still up, raises NoConnectionAvailble if not
        """
        if self.connection is None:
            raise NoConnectionAvailable()
        
        try:
            self.connection.send_fmsg(rtob(RequestType.CHECK_CONNECTED))
            msg = self.connection.recv_fmsg()
        except:
            self.__close()
            raise NoConnectionAvailable()
        
        return self.connection
    
    def capture(self, preview = True) -> Image.Image:
        """Sends capture request, preview = True captures preview, False captures main"""
        connection = self.check_connection()

        connection.send_fmsg(rtob(RequestType.CAPTURE_PREVIEW if preview else RequestType.CAPTURE_MAIN))
        
        try:
            preview_bytes = connection.recv_fmsg()

            if preview_bytes == b"":
                raise CaptureFailed()

            preview_image = Image.open(io.BytesIO(preview_bytes))

        except CaptureFailed as e:
            raise e
        except:
            self.__close()
            raise NoConnectionAvailable()

        return preview_image
    
    def power_off(self) -> None:
        """Tries to send power off signal (may fail), and terminates connection"""
        
        try:
            connection = self.check_connection()
            connection.send_fmsg(rtob(RequestType.POWER_OFF))
        finally:
            self.__close()

    def __str__(self) -> str:
        """String representation of the object"""
        if self.hostname is None or self.connection is None:
            return "<NotConnected>"

        sockname = self.connection.sock.getpeername()        

        return f"{self.hostname}@{sockname[0]}:{sockname[1]}"