from PhotoboothCtl import PhotoboothControlServer
from rpi_ws281x import PixelStrip

import logging

LED_COUNT = 8         # Number of LED pixels.
LED_PIN = 18          # GPIO pin connected to the pixels (must support PWM!).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 100  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    lights = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)

    lights.begin()

    for i in range(LED_COUNT):
        lights.setPixelColorRGB(i, 255, 255, 255)

    lights.show()

    server = PhotoboothControlServer()
    try:
        server.start("0.0.0.0", 8888)
    finally:
        server.stop()
