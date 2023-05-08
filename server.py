import cv2
import os
import socket
import logging
import numpy as np
from protocol import send_to


os.environ['OPENCV_VIDEOIO_PRIORITY_MSMF'] = '0' #Insurance for camera release

class ServerService:
    def __init__(self, cam_id=0, fps=30, res_h=1080, res_w=1920, compress_quailty=50, RUN=True):
        self.cam = cv2.VideoCapture(cam_id)             # cam = cv2.VideoCapture(0)
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, res_w)   # cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, res_h)  # cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.cam.set(cv2.CAP_PROP_FPS, fps)             # cam.set(cv2.CAP_PROP_FPS, 30)
        print(self.cam.get(cv2.CAP_PROP_FPS))
        self.encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), compress_quailty]
        self.RUN = RUN

        self.local_addr = ("0.0.0.0", 20001)

        self.frame_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.frame_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.frame_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 131072) 
        self.frame_sock.bind(self.local_addr)


    def start_listener(self):
        """Starts video request listener

        listen for video request packets
        """
        while self.RUN:
            data, addr = self.frame_sock.recvfrom(1024)
            self.handle_request(addr, data)


    def handle_request(self, addr, data):
        """Handle requests from the listener
        """
        if data == b"START STREAM":
                print("stast")
                self.remote_addr = addr
                self.capture()

    def capture(self):
        """captures video from the camera

        :param fps: how many frames per second the camera will capture
        :type fps: int
        :param res_h: height of the frame
        :type res_h: int
        :param res_w: width of the frame
        :type res_w: int
        """
        while self.RUN:
            _ ,frame = self.cam.read()
            _ , data = self.encode_frame(frame)
            print(int(self.cam.get(5)))
            send_to(self.frame_sock, self.remote_addr, data)

    def encode_frame(self, frame):
        """compress frame to lower quailty

        :param frame: cv2 frame
        :type frame: np array
        """
        result, encoded_frame = cv2.imencode('.jpg', frame, self.encode_param)
       # return result, encoded_frame
        return result, encoded_frame.tobytes()
    


def main():
    logging.basicConfig(filename='server.log', encoding='utf-8', level=logging.DEBUG)
    demo = ServerService()
    demo.start_listener()

if __name__ == "__main__":
    main()