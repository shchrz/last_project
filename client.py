import pyvirtualcam
import cv2
import socket
import binascii
import logging
import time
import signal
import numpy as np
import tkinter as tk
from threading import Thread
from protocol import Agent, Analytics
from constents import *


class Client:
    def __init__(self, fps=30, res_h=720, res_w=1280, RUN=True):
        self.fps = fps
        self.res_h = res_h
        self.res_w = res_w
        self.RUN = RUN
        self.analytics = Analytics()
        self.agent = None
        self._control_setup()
        self.set_up_camera()

    def set_up_camera(self):
        self.cam = pyvirtualcam.Camera(
            width=self.res_w,
            height=self.res_h,
            fps=self.fps,
            fmt=pyvirtualcam.PixelFormat.BGR,
            print_fps=True,
        )

    def _control_setup(self):
        self.control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.control_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.control_sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.control_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
        self.control_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
        self.control_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)

    def check_valid_data(self, data, CRC):
        logging.debug("{} | {}".format(CRC, binascii.crc32(data)))
        return CRC == binascii.crc32(data)

    def decode_frame(self, data):
        """decodes the data from bytes to a frame

        :param data: encoded frame
        :type data: bytes
        """
        data = np.frombuffer(data, dtype=np.uint8)
        print(data)
        print(type(cv2.imdecode(data, 1)))
        return cv2.imdecode(data, 1)

    def send_frame_to_camera(self, frame):
        try:
            self.cam.send(frame)
            logging.debug("Sent {} to virtual camera".format(frame[:32]))
        # self.cam.sleep_until_next_frame()
        except Exception as ex:
            logging.critical(ex)
            exit()

    def connect_server_control(self):
        self.control_sock.connect(("127.0.0.1", 20001))

    def send_analytics(self):
        while self.RUN:
            time.sleep(ANALYTICS_INTERVAL)
            self._send_analytics_data()

    def _send_analytics_data(self):
        print("start _send_analytics_data")
        frames_received = self.analytics.get_frames_received()
        packets_received = self.analytics.get_packets_received()
        msg = (
            b"FPMA|"
            + str(packets_received).encode()
            + b"|"
            + str(frames_received).encode()
        )
        # FPMA -> Frames Packets Measurement Analytics
        self._send_data(msg)
        self.analytics.reset()

    def send_start_capture(self):
        msg = b"SVCS"
        self._send_data(msg)

    def _send_data(self, data):
        print("start _send_data")
        ret = self.control_sock.send(data)
        if ret > 0:
            return self._send_data(data[ret:])
        else:
            return 0

    def exit(self, *args, **kargs):
        self.cam.close()
        self.RUN = False
        self.agent.stop_receive()
        self.receive_thread.join()

    def agent_frames_to_camera(self):
        print("started agent_frames_to_camera")
        sleep_time = 1.0 / self.fps * 2

        while self.RUN:
            data = self.agent.get_last_data()
            frame = data.get_data()
            if not frame:
                continue
            logging.info("Received {}".format(data))
            self.send_frame_to_camera(self.decode_frame(frame))
            time.sleep(sleep_time)

    def client_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        sock.bind(("0.0.0.0", 20000))

        self.connect_server_control()
        self.send_start_capture()

        self.agent = Agent(sock)
        self.receive_thread = Thread(target=self.agent.start_receive)
        self.receive_thread.start()

        self.cam_thread = Thread(target=self.agent_frames_to_camera)
        self.cam_thread.start()

        self.analytics_thread = Thread(target=self.send_analytics)
        self.analytics_thread.start()


def main():
    logging.basicConfig(filename="client.log", encoding="utf-8", level=logging.DEBUG)

    cli = Client()
    signal.signal(signal.SIGINT, cli.exit)
    cli.client_loop()


if __name__ == "__main__":
    main()
