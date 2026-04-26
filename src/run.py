from pathlib import Path

from src.Client.imagerApp import ImagerApp
from src.Imager.imagerServer import ImagerServer
from src.user_args import get_user_args

CLIENT_DEFAULTS = {
    "log-path": Path("logs/client_logs.txt"),
    "log-record-count": 50
}

SERVER_DEFAULTS = {
    "log-path": Path("logs/imager_logs.txt"),
    "log-record-count": 50
}

TYPE = {
    "client": (ImagerApp, CLIENT_DEFAULTS),
    "imager": (ImagerServer, SERVER_DEFAULTS)
}

if __name__ == "__main__":
    options = get_user_args()

    constructor, defaults = TYPE[options["type"]]
    
    for key in defaults.keys():
        user_val = options.get(key, None)
        
        if user_val is not None:
            defaults[key] = user_val

    app = constructor(*defaults.values())
    app.start()