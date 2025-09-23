import tkinter as tk
from photoboothGUI import PhotoboothGUI
import logging

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    root = tk.Tk()
    app = PhotoboothGUI(root)
    root.mainloop()