from photoboothProtocolServer import PhotoboothProtocolServer

if __name__ == "__main__":
    server = PhotoboothProtocolServer()
    try:
        server.start()
    finally:
        server.stop()