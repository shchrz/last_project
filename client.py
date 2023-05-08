import pyvirtualcam
import cv2
import socket
import binascii
import logging
import numpy as np
import tkinter as tk
from protocol import receive_from

class Client():
    def __init__(self, fps=30, res_h=720, res_w=1280, RUN=True):
        self.fps = fps
        self.res_h = res_h
        self.res_w = res_w
        self.RUN = RUN
        self.set_up_camera()

    def set_up_camera(self):
        self.cam = pyvirtualcam.Camera(width=self.res_w ,height=self.res_h, fps=self.fps, fmt=pyvirtualcam.PixelFormat.BGR, print_fps=True)

    def check_valid_data(self, data, CRC):
            logging.debug("{} | {}".format(CRC,binascii.crc32(data)))
            return CRC == binascii.crc32(data)

    def decode_frame(self, data):
        """decodes the data from bytes to a frame

        :param data: encoded frame
        :type data: bytes
        """
        data = np.frombuffer(data, dtype=np.uint8) 
        return cv2.imdecode(data, 1)

    def send_frame_to_camera(self, frame):
        self.cam.send(frame)
        #self.cam.sleep_until_next_frame()

def reveive_loop(cli):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 131072)  
    sock.bind(("0.0.0.0", 20000))

    sock.sendto(b"START STREAM",("127.0.0.1", 20001))

    while True:
        addr, CRC, data = receive_from(sock)
        if cli.check_valid_data(data, CRC):
            frame = cli.decode_frame(data)
            #print(frame.shape)
            cli.send_frame_to_camera(frame)


def main():
    logging.basicConfig(filename='client.log', encoding='utf-8', level=logging.DEBUG)
    cli = Client()
    reveive_loop(cli)


if __name__ == "__main__":
    main()
