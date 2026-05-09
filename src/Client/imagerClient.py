from pathlib import Path
from typing import Optional
from PIL import Image

from src.logs import Logger, INFO, WARN, ERROR
from src.Client.imagerClientConnection import ImagerClientConnection

TEST = Path("preview.jpg")

class ImagerClient:
    def __init__(self, logger: Logger) -> None:
        """
        Constructs an imager client which handles user inputs

        logger: logger that is being used by frontend (same logfile)
        """

        self.logger = logger
        self.imagerConnection = ImagerClientConnection(logger)

    def __log(self, type: str, msg: str):
         """
         Creates log with name of class attached
         
         type: type of log
         msg: message to log
         """
         self.logger.log(type, msg, "ImagerClient")

    def connection_repr(self) -> str:
        return str(self.imagerConnection)

    def discover(self, hostname: str) -> None:
        """
        Looks for IP address of Raspberry Pi using mDNS and tries to connect on protocol port

        hostname: string that represents the canonical hostname (raspberrypi.local)
        """
        self.__log(INFO, f"looking for {hostname}")

        ip = self.imagerConnection.discover(hostname)

        self.__log(INFO, f"found hostname at {ip}, attempting connection")
        
        self.imagerConnection.connect(ip)

        self.__log(INFO, f"connected successfully to {ip}@protocol_port")
    
    def capture_preview(self) -> Image.Image:
        """Captures a preview image"""
        self.__log(INFO, "attempting capture of preview")

        image = self.imagerConnection.capture(preview=True)

        return image
    
    def capture_main(self, filepath: Path) -> Image.Image:
        """Captures a main image"""
        if filepath.exists():
            self.__log(ERROR, f"path {filepath} already exists; aborting")
            raise FileExistsError(f"path {filepath} already exists; aborting")

        self.__log(INFO, "attempting capture of main")

        image = self.imagerConnection.capture(preview=False)

        self.__log(INFO, "received main image")

        image.save(filepath)

        self.__log(INFO, f"stored main capture at {filepath}")

        return image
    
    def power_off(self) -> None:
        """Sends power off signal"""
        self.__log(INFO, "shutting down product")
        
        self.imagerConnection.power_off()