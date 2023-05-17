import cv2
import os
import socket
import logging
import signal
import time
from threading import Thread
from protocol import Agent, Data


os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"  # Insurance for camera release


class ServerService:
    def __init__(
        self, cam_id=0, fps=10, res_h=720, res_w=1280, compress_quailty=50, RUN=True
    ):
        self.cam = cv2.VideoCapture(cam_id)  # cam = cv2.VideoCapture(0)
        self.cam.set(
            cv2.CAP_PROP_FRAME_WIDTH, 1920
        )  # cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cam.set(
            cv2.CAP_PROP_FRAME_HEIGHT, 1080
        )  # cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.cam.set(cv2.CAP_PROP_FPS, 30)  # cam.set(cv2.CAP_PROP_FPS, 30)
        print(self.cam.get(cv2.CAP_PROP_FPS))
        self.encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), compress_quailty]
        self.RUN = RUN
        self.fps = fps
        self.frame_devider = round(30 / self.fps)
        print("devider: {}".format(self.frame_devider))
        self.res_w = res_w
        self.res_h = res_h

        self.local_addr = ("0.0.0.0", 20001)

        self.frame_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.frame_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.frame_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 131072)
        self.frame_sock.bind(self.local_addr)

        self.agent = Agent(self.frame_sock, fps=self.fps)

        self.analytics_thread = Thread(target=self.print_analytics)
        self.analytics_thread.start()

    def start_listener(self):
        """Starts video request listener

        listen for video request packets
        """
        while self.RUN:
            data, addr = self.frame_sock.recvfrom(1024)
            self.handle_request(addr, data)

    def stop(self, sig, farme):
        self.RUN = False
        self.cam.release()
        self.frame_sock.close()

    def handle_request(self, addr, data):
        """Handle requests from the listener"""
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
        index = -1
        while self.RUN:
            _, frame = self.cam.read()
            index += 1
            if not index % self.frame_devider == 0:
                continue
            _, data = self.encode_frame(frame)
            data = Data(data)
            logging.info("Sending {}".format(data))
            self.agent.send_data(data, self.remote_addr)

    def encode_frame(self, frame):
        """compress frame to lower quailty

        :param frame: cv2 frame
        :type frame: np array
        """
        resized = cv2.resize(frame, (self.res_w, self.res_h), cv2.INTER_AREA)
        result, encoded_frame = cv2.imencode(".jpg", resized, self.encode_param)
        # return result, encoded_frame
        return result, encoded_frame.tobytes()

    def print_analytics(self):
        sleep_time = 5.0
        while self.RUN:
            time.sleep(sleep_time)
            analytics = self.agent.get_analytics()
            print(
                "Frame Per Second Send: {}".format(
                    analytics.get_frames_sent() / sleep_time
                )
            )
            print(
                "Packet Per Second Send: {}".format(
                    analytics.get_packets_sent() / sleep_time
                )
            )
            print(
                "Bitrate: {} Mbps".format(
                    analytics.get_bits_sent() / sleep_time / 1000000
                )
            )
            analytics.reset()


def main():
    logging.basicConfig(filename="server.log", encoding="utf-8", level=logging.DEBUG)
    demo = ServerService()

    signal.signal(signal.SIGINT, demo.stop)

    demo.start_listener()


if __name__ == "__main__":
    main()
