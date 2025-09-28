import threading
import tkinter as tk
import socket
import os
import queue
import logging

from PhotoboothCtl import PhotoboothControl
from PIL import Image, ImageTk, ImageDraw
from tkinter import ttk, filedialog, simpledialog
from dataclasses import dataclass
from typing import Optional
from enum import Enum

class RequestType(Enum):
    DISCOVER = "DISCOVER"
    CAPTUREMAIN = "CAPTURE_MAIN"
    CAPTUREPREVIEW = "CAPTURE_PREVIEW"
    POWEROFF = "POWER_OFF"

@dataclass
class UIRequest:
    req_id: int
    type: RequestType

class PhotoboothGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.logger = logging.getLogger("Photobooth")
        self.BoothCtl = PhotoboothControl(self)
        self.root.title("Camera Controller")
        self.root.geometry("600x750")
        
        # Default image (black square)
        self.default_image = Image.new('RGB', (400, 300), color='black')
        self.image_tk = ImageTk.PhotoImage(self.default_image)

        self.request_id_counter = 0
        self.request_queue: queue.Queue[UIRequest] = queue.Queue()
        self.backend_thread: Optional[threading.Thread] = None

        self._setup_ui()
        self._start_backend()
        
    def _setup_ui(self):
        # Top frame for address input and discover button
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Address input
        self.address_var = tk.StringVar(value="raspberrypi.local")
        self.address_entry = ttk.Entry(top_frame, textvariable=self.address_var, width=30)
        self.address_entry.grid(row=0, column=0, padx=(0, 10), sticky=(tk.W, tk.E))
        
        # Discover button
        self.discover_btn = ttk.Button(top_frame, text="Discover", command=lambda: self._send_request(RequestType.DISCOVER))
        self.discover_btn.grid(row=0, column=1, sticky=tk.W)
        
        # Preview capture button
        preview_btn = ttk.Button(self.root, text="Capture Preview", command=lambda: self._send_request(RequestType.CAPTUREPREVIEW))
        preview_btn.grid(row=1, column=0, padx=10, pady=10, sticky=(tk.W, tk.E))
        
        # Image display area
        self.image_label = ttk.Label(self.root, image=self.image_tk)
        self.image_label.grid(row=2, column=0, padx=10, pady=10)
        
        # Main capture button
        main_btn = ttk.Button(self.root, text="Capture Main", command=lambda: self._send_request(RequestType.CAPTUREMAIN))
        main_btn.grid(row=3, column=0, padx=10, pady=10, sticky=(tk.W, tk.E))
        
        # Directory selection frame
        dir_frame = ttk.Frame(self.root, padding="10")
        dir_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # Directory path display
        self.dir_var = tk.StringVar(value="Select directory...")
        dir_label = ttk.Label(dir_frame, textvariable=self.dir_var, background="white", 
                             relief="sunken", padding="5")
        dir_label.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        dir_label.bind("<Button-1>", self.choose_directory)  # Click to choose directory
        
        # Browse button
        browse_btn = ttk.Button(dir_frame, text="Browse", command=self.choose_directory)
        browse_btn.grid(row=0, column=1, sticky=tk.W)
        
        # Error display area at the bottom
        logging_frame = ttk.Frame(self.root, padding="10")
        logging_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.S), pady=10)
        
        self.logging_var = tk.StringVar(value="")
        self.logging_label = ttk.Label(logging_frame, textvariable=self.logging_var, 
                               foreground="red", wraplength=550, justify=tk.LEFT)
        self.logging_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        top_frame.columnconfigure(0, weight=1)
        dir_frame.columnconfigure(0, weight=1)
        logging_frame.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)
        
    def _start_backend(self):
        """Start thread that does backend work"""
        self.backend_thread = threading.Thread(target=self._backend_worker, daemon=True)
        self.backend_thread.start()

    def _backend_worker(self):
        """Thread function that takes requests and feeds them into the photobooth controller"""
        while True:
            try:
                # Get request from queue (with timeout to allow shutdown)
                request = self.request_queue.get(timeout=0.1)
                
                # Process the request
                if request.type == RequestType.DISCOVER:
                    self.BoothCtl.discover()
                elif request.type == RequestType.CAPTUREMAIN:
                    self.BoothCtl.capture_main()
                elif request.type == RequestType.CAPTUREPREVIEW:
                    self.BoothCtl.capture_preview()
                elif request == RequestType.POWEROFF:
                    self.BoothCtl.power_off()
                
                # Mark task as done
                self.request_queue.task_done()
                
            except queue.Empty:
                continue

            except Exception as e:
                continue

    def _get_next_request_id(self):
        """Returns a new request id"""
        self.request_id_counter += 1
        return self.request_id_counter

    def _send_request(self, type: RequestType):
        """Places a request for the backend"""
        request = UIRequest(self._get_next_request_id, type)
        self.request_queue.put(request)

    def log_info(self, msg: str):
        """Logs info to user in black"""
        self.logger.info(msg)
        self.logging_label.configure(foreground="black")
        self.logging_var.set("INFO - " + msg)

    def log_error(self, msg: str):
        """Logs error to user in red"""
        self.logger.error(msg)
        self.logging_label.configure(foreground="red")
        self.logging_var.set("ERROR - " + msg)

    def get_hostname(self) -> Optional[str]:
        """Returns a hostname or None if hostname is empty"""
        hostname = self.address_var.get()
        if not hostname:
            return None
        return hostname
    
    def get_dirname(self) -> Optional[str]:
        """Returns the selected directory"""
        directory = self.dir_var.get()
        if directory == "Select directory...":
            return None
        return directory

    def request_fname(self) -> Optional[str]:
        return simpledialog.askstring(title="Name Image", prompt="Save image as:", initialvalue="image.jpg")

    def show_image(self, image: Image):
        """Update the image display with a new image"""
        image.save("preview.jpg")
        if image.size != (400, 300):
            image = image.resize((400, 300))

        self.image_tk = ImageTk.PhotoImage(image)
        self.image_label.configure(image=self.image_tk)
        
    def capture_main(self):
        """Handle main capture button click"""
        print("Capturing main image...")

        directory = self.dir_var.get()
        
        if directory == "Select directory...":
            self.show_error("Error: Please select a directory first!")
            return

        if not self.PBClient.isConnected():
            self.show_error("Error: not connected to pi")    

        main_image = self.PBClient.getMain()

        if not main_image:
            self.show_error("Error: failed to fetch main")
            return
        
        name = "name.png"
        main_image.save(name, "PNG")
        self.show_message(f"Added image as {name}")
        
    def choose_directory(self, event=None):
        """Open directory chooser dialog"""
        directory = filedialog.askdirectory(
            title="Select directory to save images",
            initialdir=os.getcwd()
        )
        
        if directory:
            self.dir_var.set(directory)
            self.log_info(f"Selected directory: {directory}")