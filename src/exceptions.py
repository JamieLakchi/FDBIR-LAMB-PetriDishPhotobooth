class HostNotFound(Exception):
    pass
   
class ConnectionRefused(Exception):
    pass

class NoConnectionAvailable(Exception):
    def __str__(self) -> str:
        return "no connection is currently available"

class SocketReceivedBytesEmpty(Exception):
    def __str__(self) -> str:
        return "received bytes object from socket was None"
    
class CaptureFailed(Exception):
    def __str__(self) -> str:
        return "failed to capture image"