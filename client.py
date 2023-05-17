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
from protocol import Agent, Data


class Client:
    def __init__(self, fps=10, res_h=720, res_w=1280, RUN=True):
        self.fps = fps
        self.res_h = res_h
        self.res_w = res_w
        self.RUN = RUN
        self.agent = None
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
        # print(data)
        # print(type(cv2.imdecode(data, 1)))
        return cv2.imdecode(data, 1)

    def send_frame_to_camera(self, frame):
        try:
            self.cam.send(frame)
            logging.debug("Sent {} to virtual camera".format(frame[:32]))
        # self.cam.sleep_until_next_frame()
        except Exception as ex:
            logging.critical(ex)
            exit()

    def exit(self, *args, **kargs):
        self.cam.close()
        self.RUN = False
        self.agent.stop_receive()
        self.receive_thread.join()
        self.analytics_thread.join()

    def receive_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        sock.bind(("0.0.0.0", 20000))

        sock.sendto(b"START STREAM", ("127.0.0.1", 20001))

        self.agent = Agent(sock, fps=self.fps)
        self.receive_thread = Thread(target=self.agent.start_receive)
        self.receive_thread.start()

        self.analytics_thread = Thread(target=self.print_analytics)
        self.analytics_thread.start()

        sleep_time = 1.0 / self.fps  # TODO: change to var

        while self.RUN:
            data, serial = self.agent.get_last_data()
            # print("Got last data - {}".format(serial))
            frame = data.get_data()
            if not frame:
                time.sleep(sleep_time / 10)
                continue
            # logging.info("Received {}".format(data))
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
            print("CRC Error: {}%".format(analytics.get_packet_CRC_error()))
            print("")
            analytics.reset()


def main():
    logging.basicConfig(filename="client.log", encoding="utf-8", level=logging.DEBUG)

    cli = Client()
    signal.signal(signal.SIGINT, cli.exit)
    cli.receive_loop()


if __name__ == "__main__":
    main()
