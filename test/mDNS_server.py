# Small mDNS server that can be used for testing/debugging
# Advertises test.local to localhost@8888

import socket
import threading
from zeroconf import ServiceInfo, Zeroconf

IP = "127.0.0.1"
PORT = 8888

SERVICE_NAME = "test"
SERVICE_TYPE = "_http._tcp.local."
FULL_NAME = f"{SERVICE_NAME}.{SERVICE_TYPE}"

class MDNSTestServer:
    def __init__(self):
        self.zeroconf = None
        self.service_info = None
        self.running = False
        
        self.service_info = ServiceInfo(
            SERVICE_TYPE,
            FULL_NAME,
            addresses=[socket.inet_aton(IP)],
            port=PORT,
            properties={'description': 'Python Test Server'},
            server=SERVICE_NAME + ".local.",
        )
        
        self.zeroconf = Zeroconf()
        self.zeroconf.register_service(self.service_info)

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.server_socket.bind(('0.0.0.0', PORT))
        self.server_socket.listen(5)
        self.server_socket.settimeout(5)

        print(f"Advertising {SERVICE_NAME}.local@{IP}:{PORT}")
    
    def start_server(self):
        """Start the TCP server"""
        self.running = True
        
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                print(f"Client connected from: {client_address}")
                
                thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                thread.start()
                
            except socket.timeout:
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(e)
                break
        
        self.server_socket.close()
    
    def handle_client(self, client_socket, client_address):
        """Handle incoming connections"""
        try:
            print("connected")
        finally:
            client_socket.close()
    
    def run(self):
        try:
            self.start_server()
        except Exception as e:
            print(e)
        except KeyboardInterrupt:
            print("Shutting down...")
        finally:
            self.stop()
    
    def stop(self):
        self.running = False
        if self.zeroconf:
            self.zeroconf.unregister_service(self.service_info)
            self.zeroconf.close()
            print("mDNS service stopped")

import sys

from pathlib import Path

from src.connections import Connection, RequestType

class ImagerServerStub(MDNSTestServer):
    def __init__(self):
        super().__init__()

    def handle_client(self, client_socket, client_address):
        try:
            print("client connected")
            print("client_socket:")
            print(f"\ttype: {type(client_socket)}")
            print(f"\tvalue:{client_socket}")
            print("client_address:")
            print(f"\ttype: {type(client_address)}")
            print(f"\tvalue: {client_address}")
            connection = Connection(client_socket)
            while self.running:
                request = connection.recv_fmsg()
                request_type = RequestType(int.from_bytes(request, "little"))
                
                print("received request: ", request_type.name)
                if request_type == RequestType.CHECK_CONNECTED:
                    connection.send_fmsg(b"")

                elif request_type == RequestType.CAPTURE_PREVIEW:
                    connection.send_file(Path("preview.jpg"))

                elif request_type == RequestType.CAPTURE_MAIN:
                    connection.send_file(Path("preview.jpg"))

                elif request_type == RequestType.POWER_OFF:
                    break

        except Exception as e:
            print(e)
        finally:
            client_socket.close()


if __name__ == "__main__":
    server = ImagerServerStub()
    server.run()