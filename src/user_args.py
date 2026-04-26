import argparse

from pathlib import Path

NAME = "Petri dish imager"
DESCRIPTION = "This repository holds the files to control a RPI 4B and camera via a GUI and a socket connection"
EPILOG = "If you are a member of UAntwerpen and need more help, feel free to send an email to jamie.lakchi@student.uantwerpen.be."

def get_user_args() -> dict:
    """Returns user arguments"""
    argParser = argparse.ArgumentParser(prog=NAME,
                                        description=DESCRIPTION,
                                        epilog=EPILOG)
    argParser.add_argument("-t", "--type", help="which script to run, client or imager", action="store", required=True, choices=["client", "imager"])
    argParser.add_argument("--log-path", help="Filepath of where to store logs", action="store", default=None, type=Path)
    argParser.add_argument("--log-record-count", help="Decides number of logs that are kept", action="store", default=None, type=int)
    args = argParser.parse_args()

    options = {
        "type" : args.type,
        "log-path" : args.log_path,
        "log-record-count" : args.log_record_count
    }

    return options