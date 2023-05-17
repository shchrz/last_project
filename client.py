import pyvirtualcam
import cv2
import socket
import binascii
import logging, logging.handlers
import time
import signal
import numpy as np
import tkinter as tk
from threading import Thread, Lock
from protocol import Agent, Data

logger = logging.getLogger(__name__)


class Client:
    def __init__(
        self,
        addr=("127.0.0.1", 20001),
        output_camera=False,
        fps=30,
        res_h=720,
        res_w=1280,
        RUN=True,
    ):
        self.fps = fps
        self.res_h = res_h
        self.res_w = res_w
        self.RUN = RUN
        self.addr = addr
        self.lock = Lock()
        self.agent = None
        self.output_camera = output_camera
        if self.output_camera:
            self.set_up_camera()

    def set_up_camera(self):
        self.cam = pyvirtualcam.Camera(
            width=self.res_w,
            height=self.res_h,
            fps=self.fps,
            fmt=pyvirtualcam.PixelFormat.BGR,
            print_fps=False,
        )

    def check_valid_data(self, data, CRC):
        logging.debug("{} | {}".format(CRC, binascii.crc32(data)))
        return CRC == binascii.crc32(data)

    def decode_frame(self, data):
        """decodes the data from bytes to a frame

        :param data: encoded frame
        :type data: bytes
        """
        data = np.frombuffer(data, dtype=np.uint8)
        return cv2.imdecode(data, 1)

    def send_frame_to_camera(self, frame):
        try:
            if not self.output_camera:
                cv2.imshow("Perview {}".format(self.port), frame)
                cv2.waitKey(1)
            else:
                self.cam.send(frame)
        # self.cam.sleep_until_next_frame()
        except Exception as ex:
            logging.critical(ex)
            exit()

    def exit(self, *args, **kargs):
        if self.output_camera:
            self.cam.close()
        self.lock.acquire()
        self.RUN = False
        self.agent.stop_receive()
        self.lock.release()
        self.tcp_sock.close()
        self.udp_sock.close()

        self.receive_thread.join()

    def receive_loop(self):
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_sock.settimeout(5)

        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_sock.connect(self.addr)

        self.port = self.tcp_sock.recv(16).decode()
        self.udp_sock.bind(("0.0.0.0", int(self.port)))

        self.agent = Agent(self.udp_sock, self.tcp_sock, self.addr, fps=self.fps)
        self.receive_thread = Thread(target=self.agent.start_receive)
        self.receive_thread.start()

        logger.info("Starting analytics thread")
        self.analytics_thread = Thread(target=self.print_analytics)
        self.analytics_thread.start()
        logger.info("Started analytics thread")

        sleep_time = 1.0 / self.fps  # TODO: change to var

        while self.RUN:
            data, serial = self.agent.get_last_data()
            logger.debug("Got last data - {}".format(serial))
            frame = data.get_data()
            if not frame:
                time.sleep(sleep_time / 10)
                continue
            logger.debug("Received {}".format(data))
            self.send_frame_to_camera(self.decode_frame(frame))
            # time.sleep(sleep_time)

    def print_analytics(self):
        sleep_time = 5.0
        while self.RUN:
            time.sleep(sleep_time)
            analytics = self.agent.get_analytics()
            print(
                "Receive FPS: {}".format(analytics.get_frames_received() / sleep_time)
            )
            print("Actual FPS: {}".format(analytics.get_good_frames() / sleep_time))
            print(
                "Bitrate: {} Mbps".format(
                    analytics.get_bits_received() / sleep_time / 1000000
                )
            )
            print("PPS: {}".format(analytics.get_packets_received() / sleep_time))
            print("CRC Error Percentage: {}%".format(analytics.get_packet_CRC_error()))
            print("CRC Errors: {}".format(analytics.get_packet_CRC()))
            print("")
            analytics.reset()

            # if not self.agent.is_alive():
            # self.exit()


def main():
    """
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # add formatter to ch
    ch.setFormatter(formatter)

    fh_DEBUG = logging.handlers.RotatingFileHandler("client_debug.log")
    fh_DEBUG.setLevel(logging.DEBUG)

    fh_INFO = logging.handlers.RotatingFileHandler("client.log")
    fh_INFO.setLevel(logging.INFO)

    # add ch to logger
    logger.addHandler(ch)
    logger.addHandler(fh_DEBUG)
    logger.addHandler(fh_INFO)
    """
    cli = Client()
    signal.signal(signal.SIGINT, cli.exit)
    cli.receive_loop()


if __name__ == "__main__":
    main()
