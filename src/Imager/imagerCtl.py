import subprocess

from pathlib import Path

from src.logs import Logger, INFO, WARN, ERROR
from src.exceptions import CaptureFailed

LED_COUNT = 8         # Number of LED pixels.
LED_PIN = 18          # GPIO pin connected to the pixels (must support PWM!).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 100  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0

class ImagerCtl:
    def __init__(self, logger: Logger) -> None:
        self.logger = logger

    def __log(self, type: str, msg: str):
         """
         Creates log with name of class attached
         
         type: type of log
         msg: message to log
         """
         self.logger.log(type, msg, "ImagerCtl")

    def capture_main(self, temp_storage_path=Path("/tmp/main_img.jpg")) -> Path:
        """
        Captures main image

        temp_storage_path: place to store captured image temporarily
        return: path of captured image
        """
        self.__log(INFO, "capturing main")

        exit_code = subprocess.run(["rpicam-still",
                            "-o", temp_storage_path,
                            "--width", "8000",
                            "--height", "6000",
                            "-n", "--autofocus-on-capture",
                            "--denoise", "cdn_off"]).returncode

        if exit_code:
            self.__log(ERROR, "failed to capture main")
            raise CaptureFailed()
        
        return temp_storage_path

    def capture_preview(self, temp_storage_path=Path("/tmp/preview_img.jpg")) -> Path:
        """
        Captures preview image

        temp_storage_path: place to store captured image temporarily
        return: path of captured image
        """
        exit_code = subprocess.run(["rpicam-still",
                            "-o", temp_storage_path,
                            "--width", "2312",
                            "--height", "1736",
                            "-n", "--autofocus-on-capture",
                            "--denoise", "cdn_off",
                            "--awb", "tungsten"]).returncode
        
        if exit_code:
            self.__log(ERROR, "failed to capture preview")
            raise CaptureFailed()

        return temp_storage_path

    def power_off(self) -> None:
        """
        Powers of device
        """
        self.__log(INFO, "shutting down")
        subprocess.run(["sudo", "shutdown", "now"])