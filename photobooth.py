import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk, ImageDraw
import socket
from photoboothProtocolClient import PhotoboothProtocolClient
import os

class PhotoboothGUI:
    def __init__(self, root):
        self.root = root
        self.PBClient = PhotoboothProtocolClient()
        self.root.title("Camera Controller")
        self.root.geometry("600x750")
        
        # Default image (black square)
        self.default_image = Image.new('RGB', (400, 300), color='black')
        self.image_tk = ImageTk.PhotoImage(self.default_image)
        
        self.PBClient.onLostConnection(lambda : self.show_error("Error: lost connection to pi"))

        self.setup_ui()
        
    def setup_ui(self):
        # Top frame for address input and discover button
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Address input
        self.address_var = tk.StringVar(value="raspberrypi.local")
        self.address_entry = ttk.Entry(top_frame, textvariable=self.address_var, width=30)
        self.address_entry.grid(row=0, column=0, padx=(0, 10), sticky=(tk.W, tk.E))
        
        # Discover button
        self.discover_btn = ttk.Button(top_frame, text="Discover", command=self.discover)
        self.discover_btn.grid(row=0, column=1, sticky=tk.W)
        
        # Preview capture button
        preview_btn = ttk.Button(self.root, text="Capture Preview", command=self.capture_preview)
        preview_btn.grid(row=1, column=0, padx=10, pady=10, sticky=(tk.W, tk.E))
        
        # Image display area
        self.image_label = ttk.Label(self.root, image=self.image_tk)
        self.image_label.grid(row=2, column=0, padx=10, pady=10)
        
        # Main capture button
        main_btn = ttk.Button(self.root, text="Capture Main", command=self.capture_main)
        main_btn.grid(row=3, column=0, padx=10, pady=10, sticky=(tk.W, tk.E))
        
        # Directory selection frame
        dir_frame = ttk.Frame(self.root, padding="10")
        dir_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # Directory path display
        self.dir_var = tk.StringVar(value="Select directory...")
        dir_label = ttk.Label(dir_frame, textvariable=self.dir_var, background="white", 
                             relief="sunken", padding="5")
        dir_label.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        dir_label.bind("<Button-1>", self.choose_directory)  # Click to choose directory
        
        # Browse button
        browse_btn = ttk.Button(dir_frame, text="Browse", command=self.choose_directory)
        browse_btn.grid(row=0, column=1, sticky=tk.W)
        
        # Error display area at the bottom
        error_frame = ttk.Frame(self.root, padding="10")
        error_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.S), pady=10)
        
        self.error_var = tk.StringVar(value="")
        self.error_label = ttk.Label(error_frame, textvariable=self.error_var, 
                               foreground="red", wraplength=550, justify=tk.LEFT)
        self.error_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        top_frame.columnconfigure(0, weight=1)
        dir_frame.columnconfigure(0, weight=1)
        error_frame.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)
        
    def connected(self):
        self.address_entry.config(foreground="green")
        self.discover_btn.config(text="shutdown", command=self.shutdown)

    def disconnected(self):
        self.show_message("pi disconnected")
        self.address_entry.config(foreground="black")
        self.discover_btn.config(text="discover", command=self.discover)

    def discover(self):
        """Handle discover button click"""
        address = self.address_var.get()
        self.clear_error()
        print(f"Discovering device at: {address}")
        
        if not address:
            self.show_error("Error: Address cannot be empty!")
            return
            
        try:
            pi_ip = socket.gethostbyname(address)
            print(f"Found Pi at: {pi_ip}")

            if not self.PBClient.connect(pi_ip, 8888):
                raise Exception("Failed to connect to pi")
            
            self.connected()

        except Exception as e:
            print(f"Could not resolve {address}: {e}")
            self.address_entry.config(foreground="red")
            self.show_error("Error: failed to connect to pi")
    
    def shutdown(self):
        self.PBClient.poweroff()
        self.disconnected()

    def capture_preview(self):
        """Handle preview capture button click"""
        self.clear_error()
        print("Capturing preview...")
        
        if not self.PBClient.isConnected():
            self.show_error("Error: not connected to pi")
            return
            
        preview_image = self.PBClient.getPreview()

        if not preview_image:
            self.show_error("Error: failed to fetch preview")
            preview_image = Image.new('RGB', (400, 300), color=(50, 100, 150))
            draw = ImageDraw.Draw(preview_image)
            draw.text((150, 140), "Preview Image", fill=(255, 255, 255))
        
        self.update_image(preview_image)
        
    def capture_main(self):
        """Handle main capture button click"""
        self.clear_error()
        print("Capturing main image...")

        directory = self.dir_var.get()
        
        if directory == "Select directory...":
            self.show_error("Error: Please select a directory first!")
            return

        if not self.PBClient.isConnected():
            self.show_error("Error: not connected to pi")    

        main_image = self.PBClient.getMain()

        if not main_image:
            self.show_error("Error: failed to fetch main")
            return
        
        name = "name.png"
        main_image.save(name, "PNG")
        self.show_message(f"Added image as {name}")

    def update_image(self, image):
        """Update the image display with a new image"""
        # Resize image to fit the display area if needed
        if image.size != (400, 300):
            image = image.resize((400, 300))
        
        self.image_tk = ImageTk.PhotoImage(image)
        self.image_label.configure(image=self.image_tk)
        
    def choose_directory(self, event=None):
        """Open directory chooser dialog"""
        self.clear_error()
        directory = filedialog.askdirectory(
            title="Select directory to save images",
            initialdir=os.getcwd()
        )
        
        if directory:
            self.dir_var.set(directory)
            print(f"Selected directory: {directory}")

    def show_message(self, message):
        """Display a message"""
        self.error_label.configure(foreground="black")
        self.error_var

    def show_error(self, message):
        """Display an error message"""
        self.error_label.configure(foreground="red")
        self.error_var.set(message)
    
    def clear_error(self):
        """Clear any error message"""
        self.error_var.set("")
        

def main():
    root = tk.Tk()
    app = PhotoboothGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()