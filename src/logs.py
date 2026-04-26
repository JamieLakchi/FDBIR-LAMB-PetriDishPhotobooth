import datetime

from typing import Optional
from pathlib import Path

# common log types as variables
INFO = "INFO"
ERROR = "ERROR"
WARN = "WARN"

def format_log(type: str, msg: str, name: Optional[str] = None) -> str:
    """
    Formats a log
    Includes time and script in which it was called
    
    type: type of log to display
    msg: message in log
    name: name to add to log (can be none)

    return: "[type] - [name]? - {%Y/%m/%d %H:%M:%S} ; {msg}\\n"
    """
    name_part = '' if name is None else f' - [{name}]'
    return f"[{type}]{name_part} - {datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')} ; {msg}\n"

class Logger:
    def __init__(self, logfile : Path = Path("logs.txt"), rollingRecordCount : Optional[int] = 50) -> None:
        """
        Constructs simple logger object that logs to stdout and a file

        logfile: path to record file of logs
        rollingRecordCount: amount of logs to keep in logfile
        """
        self.logfile = logfile
        self.logs : list[str] = []

    def log(self, type: str, msg: str, name: Optional[str] = None) -> str:
        """
        Logs an item

        type: type of log
        msg: message to log
        """
        log = format_log(type, msg, name)

        self.logs.append(log)
        self.logs = self.logs[-50:]

        self.__log_tofile(log)
        self.__log_tostdout(log)

        return log
    
    def __log_tostdout(self, log: str) -> None:
        """log message to console"""
        print(log, end="")

    def __log_tofile(self, log: str) -> None:
        """log message to logfile"""
        with self.logfile.open("w") as f:
            f.writelines(self.logs)   

if __name__ == "__main__":
    print(format_log(INFO, "hello world!"), end="")

    logger = Logger()
    logger.log(INFO, "goodbye world!")

    for i in range(50):
        logger.log(INFO, str(i))

    logger.log(INFO, "hello again world!", "test_name")