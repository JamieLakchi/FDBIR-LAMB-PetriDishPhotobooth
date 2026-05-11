from pathlib import Path
from typing import Optional

"""
Class to store shared state of the app (and have some limited functionality)
"""
class ImagerAppState:
    def __init__(self, rollingRecordCount : int = 50) -> None:
        self.rollingRecordCount = rollingRecordCount
        self.reset()

    def reset(self) -> None:
        """
        Default empty values
        """
        self.CWD: Optional[Path] = None

        self.logs: list[str] = [] 

    def addLog(self, log: str) -> None:
        """
        Add a log to rolling record of logs
        """
        self.logs.append(log)
        self.logs = self.logs[-self.rollingRecordCount:]

    def writeLogs(self, logfile: Path):
        """
        Write logs to logfile
        """
        with logfile.open("w") as f:
            f.writelines(self.logs)  