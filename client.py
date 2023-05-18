import pyvirtualcam
import cv2
import socket
import logging
import time
import signal
import numpy as np
from threading import Thread, Lock
from Crypto.Hash import SHA256
from protocol import Agent

logger = logging.getLogger(__name__)


class Client:
    def __init__(
        self,
        addr=("127.0.0.1", 20001),
        output_camera=False,
        fps=15,
        res_h=720,
        res_w=1280,
        RUN=True,
        FEC_Flag=False,
        SEC_Flag=False,
        password=None,
    ):
        """
        Initialize the Client instance.

        Args:
            addr (tuple, optional): Server address. Defaults to ("127.0.0.1", 20001).
            output_camera (bool, optional): Flag to output frames to a virtual camera. Defaults to False.
            fps (int, optional): Frames per second. Defaults to 15.
            res_h (int, optional): Resolution height. Defaults to 720.
            res_w (int, optional): Resolution width. Defaults to 1280.
            RUN (bool, optional): Flag to control the main loop. Defaults to True.
            FEC_Flag (bool, optional): Flag to enable Forward Error Correction. Defaults to False.
            SEC_Flag (bool, optional): Flag to enable Secure End-to-End Communication. Defaults to False.
            password (str, optional): Password for Secure End-to-End Communication. Defaults to None.
        """

        # Initialize instance variables
        self.fps = fps
        self.res_h = res_h
        self.res_w = res_w
        self.RUN = RUN
        self.addr = addr
        self.lock = Lock()
        self.agent = None
        self.FEC_Flag = FEC_Flag
        self.SEC_Flag = SEC_Flag
        self.key = bytes()

        # If SEC_Flag and password are set, generate a key using SHA256 encryption
        if SEC_Flag and password:
            self.key = SHA256.new(password.encode()).digest()
            logger.debug("Generated key: %s, length: %s", self.key, len(self.key))

        self.output_camera = output_camera
        if self.output_camera:
            self.set_up_camera()

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def set_up_camera(self):
        """
        Set up the camera with specified settings.
        """

        try:
            # Set up the camera with specified settings
            self.cam = pyvirtualcam.Camera(
                width=self.res_w,
                height=self.res_h,
                fps=self.fps,
                fmt=pyvirtualcam.PixelFormat.BGR,
                print_fps=False,
            )
        except Exception as ex:
            logger.exception("Failed to set up camera: %s", ex)

    def send_frame_to_camera(self, frame):
        """
        Send the frame to the camera or display it in a window.

        Args:
            frame (numpy.ndarray): Frame to be sent or displayed.
        """

        try:
            if not self.output_camera:
                # Display the frame in a window
                cv2.imshow("Preview {}".format(self.port), frame)
                cv2.waitKey(1)
            else:
                # Send the frame to the virtual camera
                self.cam.send(frame)
        except Exception as ex:
            logger.exception("Failed to send frame to camera: %s", ex)
            exit()

    def decode_frame(self, data):
        """
        Decode the data from bytes to a frame.

        Args:
            data (bytes): Encoded frame.

        Returns:
            numpy.ndarray: Decoded frame.
        """

        try:
            data = np.frombuffer(data, dtype=np.uint8)
            return cv2.imdecode(data, 1)
        except Exception as ex:
            logger.exception("Failed to decode frame: %s", ex)
            return None

    def exit(self, *args, **kargs):
        """
        Cleanup and exit the client.
        """

        try:
            if self.output_camera:
                self.cam.close()
            self.lock.acquire()
            self.RUN = False
            self.agent.stop_receive()
            self.lock.release()
            self.tcp_sock.close()
            self.udp_sock.close()

            self.receive_thread.join()
        except Exception as ex:
            logger.exception("Failed to exit: %s", ex)

    def receive_loop(self):
        """
        Main loop to receive frames and process them.
        """

        try:
            # Set up UDP and TCP sockets
            self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_sock.settimeout(5)

            self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_sock.connect(self.addr)

            # Receive the port from the TCP socket and bind the UDP socket
            self.port = self.tcp_sock.recv(16).decode()
            self.udp_sock.bind(("0.0.0.0", int(self.port)))

            # Set up the agent for receiving data
            self.agent = Agent(
                self.udp_sock,
                self.tcp_sock,
                self.addr,
                fps=self.fps,
                SEC_flag=self.SEC_Flag,
                key=self.key,
            )
            self.receive_thread = Thread(target=self.agent.start_receive)
            self.receive_thread.start()

            logger.info("Starting analytics thread")
            self.analytics_thread = Thread(target=self.print_analytics)
            self.analytics_thread.start()
            logger.info("Started analytics thread")

            sleep_time = 1.0 / self.fps

            while self.RUN:
                # Get the last received data and process the frame
                data, serial = self.agent.get_last_data()
                logger.debug("Got last data - %s", serial)
                frame = data.get_data()
                if not frame:
                    time.sleep(sleep_time / 10)
                    continue
                logger.debug("Received %s", data)
                self.send_frame_to_camera(self.decode_frame(frame))
        except Exception as ex:
            logger.exception("Error in receive loop: %s", ex)

    def print_analytics(self):
        """
        Print analytics information periodically.
        """

        try:
            sleep_time = 5.0
            while self.RUN:
                time.sleep(sleep_time)
                analytics = self.agent.get_analytics()
                logger.info(
                    "Receive FPS: %s", analytics.get_frames_received() / sleep_time
                )
                logger.info("Actual FPS: %s", analytics.get_good_frames() / sleep_time)
                logger.info(
                    "Bitrate: %s Mbps",
                    analytics.get_bits_received() / sleep_time / 1000000,
                )
                logger.info("PPS: %s", analytics.get_packets_received() / sleep_time)
                logger.info(
                    "CRC Error Percentage: %s%%", analytics.get_packet_CRC_error()
                )
                logger.info("CRC Errors: %s", analytics.get_packet_CRC())
                logger.info("")
                analytics.reset()
        except Exception as ex:
            logger.exception("Failed to print analytics: %s", ex)


def main():
    cli = Client()
    signal.signal(signal.SIGINT, cli.exit)
    cli.receive_loop()


if __name__ == "__main__":
    main()
