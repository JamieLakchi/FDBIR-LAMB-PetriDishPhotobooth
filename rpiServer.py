from photoboothProtocolServer import PhotoboothProtocolServer
from rpiCameraCtl import CameraCtl

if __name__ == "__main__":
    server = PhotoboothProtocolServer()
    camera = CameraCtl()
    server.attachCamera(camera)
    try:
        server.start()
    finally:
        server.stop()
