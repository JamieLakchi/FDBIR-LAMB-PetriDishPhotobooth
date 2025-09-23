from PhotoboothCtl import PhotoboothControlServer
from rpiCameraCtl import CameraCtl

import logging

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    server = PhotoboothControlServer()
    try:
        server.start()
    finally:
        server.stop()
