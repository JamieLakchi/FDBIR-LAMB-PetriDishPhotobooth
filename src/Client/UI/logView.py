import tkinter as tk

from src.logs import  INFO, WARN, ERROR
from src.Client.imagerApp import ImagerApp
from src.Client.eventBus import CHANGED_CWD, LOG

"""
View to see all recent logs produced by the system
"""
class LogView:
    def __init__(self, app: ImagerApp, frame: tk.Frame) -> None:
        self.app = app
        self.frame = frame
        self.id = self.app.event_bus.getId()

        self.app.event_bus.register(LOG, self.id, lambda type, msg, name:\
                                    self.app.task_frontend(self.__update_ui))

        self.__setup_ui()

    def __setup_ui(self):
        """
        Setup of the log frame UI
        """
        # Canvas with scrollbar
        self.canvas = tk.Canvas(self.frame, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.__make_scrollable(self.canvas)

        self.__update_ui()

    def __make_scrollable(self, tkwidget) -> None:
        """Helper function for scrolling bindings """
        tkwidget.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        tkwidget.bind("<Button-4>", lambda e:  self.canvas.yview_scroll(-1, "units"))
        tkwidget.bind("<Button-5>", lambda e:  self.canvas.yview_scroll(1, "units"))

    def __update_ui(self) -> None:
        """
        Update the logs in this frame on the <Log> event
        """
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        for log_string in self.app.state.logs:
            fg = "red" if (ERROR in log_string) or (WARN in log_string) else "black"
            label = tk.Label(self.scrollable_frame, text=log_string, anchor="w", justify="left", foreground=fg, wraplength=600)
            label.pack(fill="x", padx=5, pady=2)
            self.__make_scrollable(label)
        
        self.canvas.yview_moveto(1.0)