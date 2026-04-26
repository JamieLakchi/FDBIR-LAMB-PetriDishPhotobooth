import socket
import threading

from typing import Optional, Callable, Literal, Union
from pathlib import Path
from PIL import Image

from src.connections import Connection, RequestType, rtob, format_address_tuple, PROTOCOL_PORT
from src.logs import Logger, INFO, WARN, ERROR
from src.Imager.imagerCtl import ImagerCtl, CaptureFailed

class ImagerServer:
    def __init__(self, logfile : Path = Path("logs/imager_logs.txt"), rollingRecordCount : Optional[int] = 50) -> None:
        """
        ImagerServerConnection constructor

        Class to run easy server to interact with src.Client.imagerApp
        
        logfile: path to record file of logs
        rollingRecordCount: amount of logs to keep in logfile
        """
        self.logger = Logger(logfile, rollingRecordCount)

        self.imagerCtl = ImagerCtl(self.logger)

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.running = False


    def __log(self, type: str, msg: str):
         """
         Creates log with name of class attached
         
         type: type of log
         msg: message to log
         """
         self.logger.log(type, msg, "ImagerServerConnection")

    def isRunning(self) -> bool:
        """Retruns True if server is up, False if server is shutting down or is down"""
        return self.running

    def start(self, ip: str = '0.0.0.0', port: int = 8888) -> None:
        """
        Starts the server
        
        ip: IP address to start server on
        port: port to start listening on
        """
        sockname = (ip, port)
        self.__log(INFO, f"starting server on {sockname}")
        self.server_socket.bind(sockname)
        self.server_socket.listen(1)
        self.server_socket.settimeout(5)

        self.running = True
        
        while self.isRunning():
            try:
                client_socket, client_address = self.server_socket.accept()
                self.__log(INFO, f"client connected from: {client_address}")
                
                thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, f"client@{format_address_tuple(client_address)}"),
                    daemon=True
                )
                thread.start()
                
            except socket.timeout:
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.__log(ERROR, f"exception from thread {e}")
                continue
        
        self.server_socket.close()
        self.imagerCtl.power_off()

    def handle_client(self, client_socket: socket.socket, client_name: str) -> None:
        """
        Logic to handle a client connection

        Scheme is challenge-response

        client_socket: socket connection to client
        client_address: tuple containing ip and port of client
        """
        client_socket.settimeout(120)
        connection = Connection(client_socket)
        try:
            while self.isRunning():

                request = connection.recv_fmsg()
                request_type = RequestType(int.from_bytes(request, "little"))
                
                self.__log(INFO, f"from {client_name} received request: {request_type.name} ")
                if request_type == RequestType.CHECK_CONNECTED:
                    connection.send_fmsg(b"")

                elif request_type in [RequestType.CAPTURE_PREVIEW, RequestType.CAPTURE_MAIN]:
                    try:
                        fpath = self.imagerCtl.capture_main() \
                                if request_type == RequestType.CAPTURE_MAIN else \
                                self.imagerCtl.capture_preview()
                                
                        connection.send_file(fpath)

                    except CaptureFailed:
                        self.__log(ERROR, f"failed to capture image")

                        connection.send_fmsg(b"")

                elif request_type == RequestType.POWER_OFF:
                    self.running = False
                    break

        except Exception as e:
            self.__log(ERROR, f"{client_name} thread raised {e}")

        finally:
            connection.close()