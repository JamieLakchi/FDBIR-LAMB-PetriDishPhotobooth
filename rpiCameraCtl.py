import picamera2
from libcamera import controls
from rpi_ws281x import PixelStrip
from PIL import Image
import cv2

import time

LED_COUNT = 8         # Number of LED pixels.
LED_PIN = 18          # GPIO pin connected to the pixels (must support PWM!).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0


class CameraCtl:
    def __init__(self):
        self.camera = picamera2.Picamera2()
        self.lights = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)

        self._configure_cam()
        self._configure_lights()

    def _configure_cam(self):
        self.camera.still_configuration.enable_lores()

        mode = self.camera.sensor_modes[-2]
        config = self.camera.create_still_configuration(
            main={
                'size': (8000, 6000)
            },
            lores={
                'size': (1280, 720),
            },
            sensor={
                'output_size': mode['size'],
                'bit_depth': mode['bit_depth']
            }
        )

        self.camera.configure(config)
        self.camera.start()

        self.camera.set_controls({'AfMode': controls.AfModeEnum.Continuous})

        time.sleep(2)

    def _configure_lights(self):
        self.lights.begin()
        self.setNWhite(4)

    def setPixelColor(self, n, r, g, b):
        """Takes a led position, r-, g-, and b-values, and applies them"""
        self.lights.setPixelColorRGB(n, r, g, b)
        self.lights.show()

    def setNWhite(self, n):
        """Sets n leds to white"""
        for i in range(n):
            self.setPixelColor(i, 255, 255, 255)

    def getMain(self) -> Image.Image:
        """Captures main channel to PIL object"""
        return self.camera.capture_image(name="main")

    def getLores(self) -> Image.Image:
        """Captures lores channel to PIL object"""
        lores_yuv = self.camera.capture_array("lores")
        lores_rgb = cv2.cvtColor(lores_yuv, cv2.COLOR_YUV2RGB_I420)
        return Image.fromarray(lores_rgb)
