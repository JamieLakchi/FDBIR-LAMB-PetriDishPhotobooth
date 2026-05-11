import tkinter as tk

from typing import TYPE_CHECKING, Optional
from pathlib import Path
from tkinter import filedialog

from src.logs import Logger, INFO, WARN, ERROR
from src.Client.UI.pyCOLONYView import PyCOLONYView
from src.Client.UI.logView import LogView
from src.Client.imagerApp import ImagerApp
from src.Client.eventBus import CHANGED_CWD, SAVE_ANALYZED, SAVE_FINISHED

"""
Class deals with the UI of the app
"""
class ImagerAppUI:
    def __init__(self, app: ImagerApp) -> None:
        self.app = app

        self.__setup_ui()

    def __setup_ui(self) -> None:
        # Status bar above the main pane
        self.status_bar = tk.Frame(self.app.root, relief="sunken", bd=1)
        self.status_bar.pack(fill=tk.X, side=tk.TOP)
        
        # Change directory button
        self.change_project_btn = tk.Button(
            self.status_bar,
            text="Change Directory",
            command=self.change_CWD
        )
        self.change_project_btn.pack(side=tk.LEFT, padx=(10, 0), pady=2)
        
        # Current directory label
        self.current_dir_label = tk.Label(
            self.status_bar,
            text="",
            anchor="w"
        )
        self.current_dir_label.pack(side=tk.LEFT, padx=(5, 10), pady=2)
        
        # Left-right pane layout
        self.main_pane = tk.PanedWindow(
            self.app.root,
            orient=tk.HORIZONTAL,
            sashrelief="raised",
            sashwidth=6
        )
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        # top-bottom pane layouyt
        self.left_pane = tk.PanedWindow(
            self.main_pane,
            orient=tk.VERTICAL,
            sashrelief="raised",
            sashwidth=6
        )
        self.left_pane.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # pyCOLONY frame
        self.pycolony_frame = tk.Frame(self.left_pane)
        self.pycolony_view = PyCOLONYView(self.app, self.pycolony_frame)
        self.pycolony_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # logging frame
        self.logging_frame = tk.Frame(self.left_pane)
        self.logging_view = LogView(self.app, self.logging_frame)
        self.logging_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        self.left_pane.add(self.pycolony_frame, height="560")
        self.left_pane.add(self.logging_frame, height="40")

        # imager control frame
        self.imager_frame = tk.Frame(self.main_pane)

        self.main_pane.add(self.left_pane, width="800")
        self.main_pane.add(self.imager_frame, width="550")

    def change_CWD(self) -> None:
        """
        Prompts the user for a new CWD, emits CHANGED_CWD on success
        """
        if self.app.state.CWD is None:
            path = self.prompt_directory("Choose a working directory")
        else:
            path = self.prompt_directory("Choose a working directory", self.app.state.CWD)

        if path is None:
            return

        self.app.log(INFO, f"CDW has changed to {path}")
        self.app.state.CWD = path
        self.current_dir_label.config(text=str(path))
        self.__setup_save_buttons()
        self.app.emit(CHANGED_CWD, path=path)

    def __setup_save_buttons(self) -> None:
        """
        Adds the Save Analyzed and Save Finished buttons to the status bar
        """
        # Remove dir label from packing order
        self.current_dir_label.pack_forget()

        # Save analyzed button
        save_analyzed_btn = tk.Button(
            self.status_bar,
            text="Save Analyzed",
            command=self.save_analyzed
        )
        save_analyzed_btn.pack(side=tk.LEFT, pady=2)

        # Save finished button
        save_finished = tk.Button(
            self.status_bar,
            text="Save Finished",
            command=self.save_finished
        )
        save_finished.pack(side=tk.LEFT, pady=2)

        # Add dir label back
        self.current_dir_label.pack(side=tk.LEFT, padx=(5, 10), pady=2)
        
    def save_analyzed(self) -> None:
        """
        Saves data from all analyzed images
        """
        if self.app.state.CWD is None:
            self.app.log(ERROR, "Cannot save when no CWD is available")
            return
        
        self.app.log(INFO, "Saving analyzed images (plots, tsv)")

        path = self.prompt_directory(f"Choose empty directory (not in {self.app.state.CWD})", self.app.state.CWD.parent)

        if path is None:
            return
        
        if (self.app.state.CWD in path.parents) or (self.app.state.CWD == path):
            self.app.log(ERROR, f"Cannot save to CWD {self.app.state.CWD}")
            return
        
        # Check if directory is empty
        if any(path.iterdir()):
            self.app.log(ERROR, f"Chosen directory {path} is not empty")
            return

        self.app.emit(SAVE_ANALYZED, path=path)

    def save_finished(self) -> None:
        """
        Saves data from all analyzed images marked as finished
        """
        if self.app.state.CWD is None:
            self.app.log(ERROR, "Cannot save when no CWD is available")
            return

        self.app.log(INFO, "Saving analyzed images marked as finished (plots, tsv)")

        path = self.prompt_directory(f"Choose empty directory (not in {self.app.state.CWD})", self.app.state.CWD.parent)

        if path is None:
            return
        
        if (self.app.state.CWD in path.parents) or (self.app.state.CWD == path):
            self.app.log(ERROR, f"Cannot save to CWD {self.app.state.CWD}")
            return
        
        # Check if directory is empty
        if any(path.iterdir()):
            self.app.log(ERROR, f"Chosen directory {path} is not empty")
            return

        self.app.emit(SAVE_FINISHED, path=path)

    def prompt_directory(self, prompt: str = "Choose path", initialdir: Path = Path.home()) -> Optional[Path]:
        """
        Prompt the user for a directory in the filesystem
        """
        path = filedialog.askdirectory(
            title=prompt,
            initialdir=initialdir
        )
        
        if path:
            return Path(path)
