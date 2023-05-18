import tkinter as tk
from tkinter import ttk
from threading import Thread, Lock
from client import Client


class GUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Main Window")
        self.geometry("250x300")
        self.resizable(False, False)  # Disable window resizing

        self.cli_thread_running = False
        self.lock = Lock()

        self.ip_label = tk.Label(self, text="IP:")
        self.ip_label.grid(row=1, column=0, padx=(50, 5), sticky="e", pady=10)

        self.ip = tk.Entry(self)
        self.ip.insert(0, "127.0.0.1")
        self.ip.grid(row=1, column=1, pady=10, sticky="w")

        self.port_label = tk.Label(self, text="Port:")
        self.port_label.grid(row=2, column=0, padx=(50, 5), sticky="e")

        self.port = tk.Entry(self)
        self.port.insert(0, "20001")
        self.port.grid(row=2, column=1, pady=10, sticky="w")

        self.password_label = tk.Label(self, text="Password:")
        self.password_label.grid(row=3, column=0, padx=(50, 5), sticky="e")

        self.password = tk.Entry(self, show="*")
        self.password.insert(0, "123456")
        self.password.grid(row=3, column=1, pady=10, sticky="w")

        self.quit_button = tk.Button(self, text="Close", command=self.exit)
        self.quit_button.grid(row=4, column=0, pady=10, padx=(50, 5), sticky="w")

        self.connect_disconnect_button = tk.Button(
            self, text="Connect", command=self.connect_toggle
        )
        self.connect_disconnect_button.grid(row=4, column=1, pady=10, sticky="w")

        self.camera_label = tk.Label(self, text="Choose a camera output:")
        self.camera_label.grid(
            row=5, column=0, columnspan=2, pady=5, padx=(50, 5), sticky="w"
        )

        self.output_mode = tk.BooleanVar(value=False)  # Set mode1 as initially selected

        self.radio_webcam = tk.Radiobutton(
            self, text="Webcam", variable=self.output_mode, value=True
        )
        self.radio_webcam.grid(
            row=6, column=0, columnspan=2, pady=5, padx=(50, 5), sticky="w"
        )

        self.radio_view = tk.Radiobutton(
            self, text="View", variable=self.output_mode, value=False
        )
        self.radio_view.grid(
            row=7, column=0, columnspan=2, pady=5, padx=(50, 5), sticky="w"
        )

        self.protocol("WM_DELETE_WINDOW", self.exit)

    def connect_toggle(self):
        # Perform action based on textbox inputs
        if not self.cli_thread_running:
            addr = (self.ip.get(), int(self.port.get()))
            self.cli = Client(
                addr, output_camera=self.output_mode.get(), password=self.password.get()
            )

            self.cli_thread = Thread(target=self.cli.receive_loop)
            self.cli_thread.start()

            self.cli_thread_running = True

            self.connect_disconnect_button.config(text="Disconnect")
            self.radio_view.configure(state="disabled")
            self.radio_webcam.configure(state="disabled")
            self.ip.configure(state="disabled")
            self.port.configure(state="disabled")
        else:
            self.stop_client()

            self.connect_disconnect_button.config(text="Connect")
            self.radio_view.configure(state="normal")
            self.radio_webcam.configure(state="normal")
            self.ip.configure(state="normal")
            self.port.configure(state="normal")

    def stop_client(self):
        self.cli.exit()
        self.cli_thread.join()

        self.cli_thread_running = False

    def exit(self):
        if self.cli_thread_running:
            self.stop_client()

        print("worked")
        self.quit()


# Create the main window
window = GUI()


# Start the main event loop
window.mainloop()
