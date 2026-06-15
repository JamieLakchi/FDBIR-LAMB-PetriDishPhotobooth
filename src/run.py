from pathlib import Path
from src.user_args import get_user_args

if __name__ == "__main__":
    options = get_user_args()

    if options["type"] == "client":
        from src.Client.imagerApp import ImagerApp
        constructor = ImagerApp
        defaults = {
            "log-path": Path("logs/client_logs.txt"),
            "log-record-count": 100
        }
    else:
        from src.Imager.imagerServer import ImagerServer
        constructor = ImagerServer
        defaults = {
            "log-path": Path("logs/imager_logs.txt"),
            "log-record-count": 100
        }
    
    for key in defaults.keys():
        user_val = options.get(key, None)
        
        if user_val is not None:
            defaults[key] = user_val

    app = constructor(*defaults.values())
    app.start()