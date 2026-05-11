import tkinter as tk
import queue
import threading

from typing import Optional, Callable, Literal, Union
from pathlib import Path
from PIL import Image, ImageTk
from tkinter import ttk, filedialog
from concurrent.futures import ThreadPoolExecutor

from src.logs import format_log, INFO, WARN, ERROR
from src.Client.imagerAppState import ImagerAppState
from src.Client.eventBus import EventBus, LOG

class ImagerApp:
    def __init__(self, logfile : Path = Path("logs/client_logs.txt"), rollingRecordCount : int = 50) -> None:
        """
        ImagerApp constructor
        
        logfile: path to record file of logs
        rollingRecordCount: amount of logs to keep in logfile
        """

        from src.Client.UI.imagerAppUI import ImagerAppUI   # lazy import to prevent circular importing
                                                            # due to type annotations

        self.state = ImagerAppState(rollingRecordCount)
        self.event_bus = EventBus()

        self.system_id = self.event_bus.getId()

        self.logfile = logfile

        self.frontend_tasks : queue.Queue[Callable[[], None]] = queue.Queue()

        self.backend_tasks : queue.Queue[Callable[[], None]] = queue.Queue()
        self.backend_worker = threading.Thread(target=self.__backend_worker, daemon=True)
        self.backend_executor = ThreadPoolExecutor(max_workers=3)

        self.root = tk.Tk()
        self.root.title("Petri Dish Imager")
        self.root.geometry("1350x750")

        self.UI = ImagerAppUI(self)

    def emit(self, event:str, **kwargs):
        """
        Places an event in the backend tasks queue; event callbacks are performed in the backend
        (if frontend changes are required, use callback to place a task in the frontend queue)
        """
        self.task_backend(lambda: self.event_bus.emit(event, **kwargs))

    def log(self, type: str, message: str, name: str = "System"):
        """
        Emits log event via backend task
        """
        log = format_log(type, message, name)
        print(log, end="")
        self.state.addLog(log)
        self.state.writeLogs(self.logfile)
        self.emit(LOG, type=type, msg=message, name=name)

    def task_backend(self, task: Callable[[], None]) -> None:
        """
        Place task in backend queue; for computation, networking, etc.
        """
        self.backend_tasks.put(task)

    def task_frontend(self, task: Callable[[], None]) -> None:
        """
        Place taks in frontend queue; for changing frontend state
        """
        self.frontend_tasks.put(task)

    def __frontend_worker(self) -> None:
        """
        Method to start a thread that does frontend updates (in main thread)
        """
        try:
            command = self.frontend_tasks.get(timeout=0.01)
            command()
        except queue.Empty:
            pass
        except Exception as e:
            self.log(ERROR, str(e))

        self.root.after(30, self.__frontend_worker)

    def __dispatch_backend_executor(self, command: Callable[[], None]) -> None:
        try:
            command()
        except Exception as e:
            self.log(ERROR, str(e))

    def __backend_worker(self) -> None:
        """
        Method to start a thread that does backend work (prevents main thread from hanging)

        Uses threadpool to execute commands, can process max_workers commands at once
        """
        while True:
            try:
                command = self.backend_tasks.get(timeout=0.1)
                self.__dispatch_backend_executor(command)
            except queue.Empty:
                pass
            except Exception as e:
                self.log(ERROR, str(e))

    def start(self) -> None:
        """
        Start the application (stalls main thread by tk.Tk.mainloop())
        """
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.root.quit())
        self.backend_worker.start()
        self.__frontend_worker()
        self.root.mainloop()