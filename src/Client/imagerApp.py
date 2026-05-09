import tkinter as tk
import queue
import threading

from typing import Optional, Callable, Literal, Union
from pathlib import Path
from PIL import Image, ImageTk
from tkinter import ttk, filedialog

from src.logs import Logger, INFO, WARN, ERROR
from src.exceptions import NoConnectionAvailable
from src.Client.imagerClient import ImagerClient

# black square default image
DEFAULT_IMAGE = Image.new('RGB', (400, 300), color='black')

class ImagerApp:
    def __init__(self, logfile : Path = Path("logs/client_logs.txt"), rollingRecordCount : Optional[int] = 50) -> None:
        """
        ImagerApp constructor
        
        logfile: path to record file of logs
        rollingRecordCount: amount of logs to keep in logfile
        """
        self.logger = Logger(logfile, rollingRecordCount)

        self.root = tk.Tk()
        self.root.title("Camera Controller")
        self.root.geometry("600x750")

        self.frontend_responses : queue.Queue[Callable[[], None]] = queue.Queue()
        self.backend_requests : queue.Queue[Callable[[], None]] = queue.Queue()
        self.backend_worker = threading.Thread(target=self.__backend_worker, daemon=True)

        self.imagerClient = ImagerClient(self.logger)

    def __log(self, type: str, msg: str) -> None:
        """
        Logs an item

        type: type of log
        msg: message to log
        """
        if type in [WARN, ERROR]:
            self.logging_label.configure(foreground="red")
        else:
            self.logging_label.configure(foreground="black")
        log = self.logger.log(type, msg, "ImagerApp")
        self.logging_var.set(log)

    def __backend_log(self, type: str, msg: str) -> None:
        """
        Thread safe version of log
        """
        self.frontend_responses.put(lambda: self.__log(type, msg))

    def __frontend_worker(self) -> None:
        """
        Method to start a thread that does frontend updates (in main thread)
        """
        try:
            command = self.frontend_responses.get(timeout=0.01)
            command()
        except queue.Empty:
            pass
        except Exception as e:
            self.__log(ERROR, str(e))

        self.root.after(50, self.__frontend_worker)

    def __backend_worker(self) -> None:
        """
        Method to start a thread that does backend work (prevents main thread from hanging)
        """
        while True:
            try:
                command = self.backend_requests.get(timeout=0.1)
                command()
            except queue.Empty:
                pass
            except Exception as e:
                self.__backend_log(ERROR, str(e))

    def __discover(self) -> None:
        """
        Backend method to discover IP using mDNS and connect to RPI
        """
        hostname = self.address_var.get()

        if hostname is None:
            self.__backend_log(ERROR, "no hostname provided")
            return
        
        self.__backend_log(INFO, f"looking for {hostname}")
        self.imagerClient.discover(hostname)
            
        self.__backend_log(INFO, f"connected to {self.imagerClient.connection_repr()}")

        self.frontend_responses.put(lambda: self.__switch_discover_btn("Shutdown"))

    def __capture_preview(self) -> None:
        self.__backend_log(INFO, f"capturing preview")

        preview_image = self.imagerClient.capture_preview()

        def complete():
            """
            Place image in display area
            """
            if preview_image is None:
                self.__log(ERROR, "failed to fetch preview")
                return
            
            self.__display_image(preview_image)
            self.__log(INFO, "showing preview image")

        self.frontend_responses.put(complete)

    def __capture_main(self) -> None:
        directory = self.dir_var.get()

        if directory == "Select directory...":
            self.__backend_log(ERROR, "please select a directory")
            return
        
        fname = self.fname_var.get()

        if fname == "":
            self.__backend_log(ERROR, "please choose a file name")
            return
        
        fpath = Path(directory) / Path(fname)

        self.__backend_log(INFO, f"capturing main")

        self.imagerClient.capture_main(fpath)
        self.__backend_log(INFO, f"captured main (stored at {fpath})")

    def __power_off(self) -> None:
        try:
            self.imagerClient.power_off()
            self.__backend_log(INFO, f"powering off RPI (wait a moment before unplugging)")
        except:
            self.__backend_log(ERROR, "no connection found")
        finally:
            self.frontend_responses.put(lambda: self.__switch_discover_btn("Discover"))

    def __setup_ui(self) -> None:
        """
        Set up the user interface elements and assign certain variables
        """
        # Top frame for address input and discover button
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.grid(row=0, column=0, sticky=tk.W + tk.E)
        
        # Address input
        self.address_var = tk.StringVar(value="raspberrypi.local")
        self.address_entry = ttk.Entry(top_frame, textvariable=self.address_var, width=30)
        self.address_entry.grid(row=0, column=0, padx=(0, 10), sticky=tk.W + tk.E)
        
        # Discover button
        self.discover_btn = ttk.Button(top_frame, text="Discover", command=lambda: self.backend_requests.put(self.__discover))
        self.discover_btn.grid(row=0, column=1, sticky=tk.W)
        
        # Preview capture button
        preview_btn = ttk.Button(self.root, text="Capture Preview", command=lambda: self.backend_requests.put(self.__capture_preview))
        preview_btn.grid(row=1, column=0, padx=10, pady=10, sticky=tk.W + tk.E)
        
        # Image display area
        self.image_tk = ImageTk.PhotoImage(DEFAULT_IMAGE)
        self.image_label = ttk.Label(self.root, image=self.image_tk)
        self.image_label.grid(row=2, column=0, padx=10, pady=10)
        
        # Main capture button
        main_btn = ttk.Button(self.root, text="Capture Main", command=lambda: self.backend_requests.put(self.__capture_main))
        main_btn.grid(row=3, column=0, padx=10, pady=10, sticky=tk.W + tk.E)
        
        # Directory selection frame
        dir_frame = ttk.Frame(self.root, padding="10")
        dir_frame.grid(row=4, column=0, sticky=tk.W + tk.E, pady=10)
        
        # Directory path display
        self.dir_var = tk.StringVar(value="Select directory...")
        dir_label = ttk.Label(dir_frame, textvariable=self.dir_var, background="white", 
                             relief="sunken", padding="5")
        dir_label.grid(row=0, column=0, sticky=tk.W + tk.E, padx=(0, 10))
        dir_label.bind("<Button-1>", func=self.__choose_directory)  # Click to choose directory
        
        # Filename input
        self.fname_var = tk.StringVar(value="image.jpg")
        self.fname_entry = ttk.Entry(dir_frame, textvariable=self.fname_var)
        self.fname_entry.grid(row=0, column=1, sticky=tk.E)
        
        # Error display area at the bottom
        logging_frame = ttk.Frame(self.root, padding="10")
        logging_frame.grid(row=5, column=0, sticky=tk.W + tk.E + tk.S, pady=10)
        
        self.logging_var = tk.StringVar(value="Starting up...")
        self.logging_label = ttk.Label(logging_frame, textvariable=self.logging_var, 
                               foreground="black", wraplength=550, justify=tk.LEFT)
        self.logging_label.grid(row=0, column=0, sticky=tk.W + tk.E)
        
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        top_frame.columnconfigure(0, weight=1)
        dir_frame.columnconfigure(0, weight=1)
        logging_frame.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

    def __choose_directory(self, event: tk.Event) -> None:
        """Open directory chooser dialog"""
        directory = filedialog.askdirectory(
            title="Select directory to save images",
            initialdir=Path.cwd()
        )
        
        if directory:
            self.dir_var.set(directory)
            self.__log(INFO, f"Selected directory: {directory}")

    def __display_image(self, image: Image.Image):
        """Update the image display with a new image"""
        image.save(Path("__current_preview.jpg"))
        
        if image.size != (400, 300):
            image = image.resize((400, 300))

        self.image_tk = ImageTk.PhotoImage(image)
        self.image_label.configure(image=self.image_tk)

    def __switch_discover_btn(self, newFunction : Union[Literal["Discover"],Literal["Shutdown"]]) -> None:
        if newFunction == "Discover":
            self.discover_btn.configure(text="Discover", command=lambda: self.backend_requests.put(self.__discover))
        else:
            self.discover_btn.configure(text="Shutdown", command=lambda: self.backend_requests.put(self.__power_off))

    def start(self) -> None:
        """
        Start the application (stalls main thread by tk.Tk.mainloop())
        """
        self.__setup_ui()
        self.__log(INFO, "Application ready")
        self.backend_worker.start()
        self.__frontend_worker()
        self.root.mainloop()


if __name__ == "__main__":

    app = ImagerApp()
    app.start()

