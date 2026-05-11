import tkinter as tk

from typing import Optional, Literal, Union
from pathlib import Path
from PIL import Image, ImageTk
from tkinter import ttk

from src.Client.eventBus import CHANGED_CWD, IMAGE_SAVED
from src.logs import INFO, ERROR
from src.Client.imagerClient import ImagerClient
from src.Client.imagerApp import ImagerApp

# black square default image
DEFAULT_IMAGE = Image.new('RGB', (400, 300), color='black')

"""
Class describes UI and behaviour of the imager control pane
"""
class ControllerView:
    def __init__(self, app: ImagerApp, frame: tk.Frame) -> None:
        self.app = app
        self.frame = frame
        self.id = self.app.event_bus.getId()

        self.save_dir: Optional[Path] = None

        self.imagerClient = ImagerClient(self.__log)

        self.app.event_bus.register(CHANGED_CWD, self.id, self.__setup_ui)

        if not self.app.state.CWD is None:
            self.__setup_ui(self.app.state.CWD)

    def __log(self, type: str, msg: str) -> None:
        """
        Logs under ImagerController name
        """
        self.app.log(type, msg, "ImagerController")

    def _discover(self) -> None:
        """
        Backend method to discover IP using mDNS and connect to RPI
        """
        hostname = self.address_var.get()

        if hostname is None:
            self.__log(ERROR, "no hostname provided")
            return

        if self.imagerClient.discover(hostname) is None:
            return

        self.app.task_frontend(lambda: self._switch_discover_btn("Shutdown"))

    def _capture_preview(self) -> None:
        """backend method for captring a preview (lower resolution) image"""
        try:
            preview_image = self.imagerClient.capture_preview()

            if preview_image is None:
                return

            self.app.task_frontend(lambda: self._complete_capture(preview_image))
        except Exception as e:
            self.app.task_frontend(lambda: self._set_capture_buttons(disabled=False))
            raise e

    def _capture_main(self) -> None:
        """backend method for captring a preview (higher resolution) image"""
        try:
            if self.save_dir is None:
                self.__log(ERROR, "please select a directory")
                self.app.task_frontend(lambda: self._set_capture_buttons(disabled=False))
                return
            
            fname = self.fname_var.get()

            if fname == "":
                self.__log(ERROR, "please choose a file name")
                self.app.task_frontend(lambda: self._set_capture_buttons(disabled=False))
                return
            
            fpath = self.save_dir / Path(fname)

            main_image = self.imagerClient.capture_main(fpath)

            if main_image is None:
                return

            self.app.emit(IMAGE_SAVED, path=fpath)

            self.app.task_frontend(lambda: self._complete_capture(main_image))

        except Exception as e:
            self.app.task_frontend(lambda: self._set_capture_buttons(disabled=False))
            raise e

    def _start_capture(self, preview: bool) -> None:
        """
        Frontend wrapper for starting a capture
        """
        self._set_capture_buttons(disabled=True)

        if preview:
            self.app.task_backend(self._capture_preview)
        else:
            self.app.task_backend(self._capture_main)

    def _complete_capture(self, image: Image.Image) -> None:
        """
        Frontend wrapper for ending a capture
        """        
        self._display_image(image)
        self.__log(INFO, "showing new image")
        self._set_capture_buttons(disabled=False)

    def _power_off(self) -> None:
        try:
            self.imagerClient.power_off()
            self.__log(INFO, f"powering off RPI (wait a moment before unplugging)")
        except:
            self.__log(ERROR, "no connection found")
        finally:
            self.app.task_frontend(lambda: self._switch_discover_btn("Discover"))

    def __setup_ui(self, path: Path) -> None:
        """
        Set up the user interface elements and assign certain variables
        """
        # Top frame for address input and discover button
        top_frame = ttk.Frame(self.frame, padding="10")
        top_frame.grid(row=0, column=0, sticky=tk.W + tk.E)
        
        # Address input
        self.address_var = tk.StringVar(value="raspberrypi.local")
        self.address_entry = ttk.Entry(top_frame, textvariable=self.address_var, width=30)
        self.address_entry.grid(row=0, column=0, padx=(0, 10), sticky=tk.W + tk.E)
        
        # Discover button
        self.discover_btn = ttk.Button(top_frame, text="Discover", command=lambda: self.app.task_backend(self._discover))
        self.discover_btn.grid(row=0, column=1, sticky=tk.W)
        
        # Preview capture button
        self.preview_btn = ttk.Button(self.frame, text="Capture Preview", command=lambda: self._start_capture(preview=True))
        self.preview_btn.grid(row=1, column=0, padx=10, pady=10, sticky=tk.W + tk.E)
        
        # Image display area
        self.image_tk = ImageTk.PhotoImage(DEFAULT_IMAGE)
        self.image_label = ttk.Label(self.frame, image=self.image_tk)
        self.image_label.grid(row=2, column=0, padx=10, pady=10)
        
        # Main capture button
        self.main_btn = ttk.Button(self.frame, text="Capture Main", command=lambda: self._start_capture(preview=False))
        self.main_btn.grid(row=3, column=0, padx=10, pady=10, sticky=tk.W + tk.E)
        
        # Directory selection frame
        dir_frame = ttk.Frame(self.frame, padding="10")
        dir_frame.grid(row=4, column=0, sticky=tk.W + tk.E, pady=10)
        
        # Directory path display
        self.save_dir = path
        self.dir_label = ttk.Label(dir_frame, text=str(self.save_dir), background="white", relief="sunken", padding="5")
        self.dir_label.grid(row=0, column=0, sticky=tk.W + tk.E, padx=(0, 10))
        self.dir_label.bind("<Button-1>", func=self._choose_directory)  # Click to choose directory
        
        # Filename input
        self.fname_var = tk.StringVar(value="image.jpg")
        self.fname_entry = ttk.Entry(dir_frame, textvariable=self.fname_var)
        self.fname_entry.grid(row=0, column=1, sticky=tk.E)
        
        # Configure grid weights for resizing
        self.frame.columnconfigure(0, weight=1)
        top_frame.columnconfigure(0, weight=1)
        dir_frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(2, weight=1)

    def _choose_directory(self, event: tk.Event) -> None:
        if not self.save_dir is None:
            directory = self.app.UI.prompt_directory("Choose a directory to save images to", self.save_dir)
        elif not self.app.state.CWD is None:
            directory = self.app.UI.prompt_directory("Choose a directory to save images to", self.app.state.CWD)
        else:
            directory = self.app.UI.prompt_directory("Choose a directory to save images to")

        if not directory is None:
            self.save_dir = directory
            self.dir_label.config(text=str(directory))
            self.__log(INFO, f"Selected directory: {directory}")

    def _display_image(self, image: Image.Image):
        """Update the image display with a new image"""
        if image.size != (400, 300):
            image = image.resize((400, 300), Image.Resampling.LANCZOS)

        self.image_tk = ImageTk.PhotoImage(image)
        self.image_label.configure(image=self.image_tk)

    def _switch_discover_btn(self, newFunction : Union[Literal["Discover"],Literal["Shutdown"]]) -> None:
        if newFunction == "Discover":
            self.discover_btn.configure(text="Discover", command=lambda: self.app.task_backend(self._discover))
        else:
            self.discover_btn.configure(text="Shutdown", command=lambda: self.app.task_backend(self._power_off))

    def _set_capture_buttons(self, disabled: bool) -> None:
        state = "disabled" if disabled else "enabled"
        self.main_btn.configure(state=state)
        self.preview_btn.configure(state=state)