from pathlib import Path
from typing import Optional, Callable
from PIL import Image

from src.logs import INFO, ERROR
from src.Client.imagerClientConnection import ImagerClientConnection

TEST = Path("preview.jpg")

class ImagerClient:
    def __init__(self, log: Callable[[str, str], None]) -> None:
        """
        Constructs an imager client which handles user inputs
        """

        self.__log = log
        self.imagerConnection = ImagerClientConnection(log)

    def connection_repr(self) -> str:
        return str(self.imagerConnection)

    def discover(self, hostname: str) -> Optional[str]:
        """
        Looks for IP address of Raspberry Pi using mDNS and tries to connect on protocol port

        hostname: string that represents the canonical hostname (raspberrypi.local)
        """
        self.__log(INFO, f"looking for {hostname}")

        ip = self.imagerConnection.discover(hostname)

        if ip is None:
            return

        self.__log(INFO, f"found hostname at {ip}, attempting connection")
        
        if self.imagerConnection.connect(ip) is None:
            return

        self.__log(INFO, f"connected successfully to {self.imagerConnection}")

        return ip
    
    def capture_preview(self) -> Optional[Image.Image]:
        """Captures a preview image"""
        self.__log(INFO, "attempting capture of preview")

        image = self.imagerConnection.capture(preview=True)

        if image is None:
            return

        return image
    
    def capture_main(self, filepath: Path) -> Optional[Image.Image]:
        """Captures a main image"""
        if filepath.exists():
            self.__log(ERROR, f"path {filepath} already exists; aborting")
            return

        self.__log(INFO, "attempting capture of main")

        image = self.imagerConnection.capture(preview=False)

        if image is None:
            return

        self.__log(INFO, "received main image")

        image.save(filepath)

        self.__log(INFO, f"stored main capture at {filepath}")

        return image

    
    def power_off(self) -> None:
        """Sends power off signal"""        
        self.imagerConnection.power_off()