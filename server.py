import cv2
import os
import socket
import time
import logging
import signal
from threading import Thread, Lock
from protocol import Agent, Data, Analytics
from constents import *


# os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"  # Insurance for camera release


class Responder:
    def __init__(self, port=20001) -> None:
        self.local_port = port
        self.RUN = True

    def _sock_setup(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(("0.0.0.0", 55555))

    def start(self):
        self.RUN = True
        self._sock_setup()
        self.listener()

    def listener(self):
        while self.RUN:
            data, addr = self.sock.recvfrom(2048)
            self.handle_data(data, addr)

    def handle_data(self, data, addr):
        if data[:3] == b"DDSH":
            self.handle_discover(addr)
        elif data[:3] == b"PIKD":
            self.handle_picked(addr)
            self.stop()

    def handle_discover(self, addr):
        msg = b"RESH"
        self.sock.sendto(msg, addr)
        self.sock.sendto(msg, addr)

    def handle_picked(self, addr):
        msg = b"PRED|" + str(self.local_port).encode()
        self.sock.sendto(msg, addr)
        self.sock.sendto(msg, addr)

    def stop(self):
        self.RUN = False
        self.sock.close()


class ServerService:
    def __init__(
        self,
        local_port=20001,
        cam_id=0,
        fps=15,
        res_h=720,
        res_w=1280,
        compress_quailty=50,
        RUN=True,
    ):
        self.cam = cv2.VideoCapture(cam_id)
        # self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        # self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        # self.cam.set(cv2.CAP_PROP_FPS, 30)
        self.encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), compress_quailty]
        self.RUN = RUN
        self.res_h = res_h
        self.res_w = res_w
        self.fps = fps
        self.analytics = Analytics()
        self.LOCK = Lock()

        self.local_addr = ("0.0.0.0", local_port)
        self._control_setup()
        self._frame_setup()
        self.connected = False

        self.agent = Agent(
            self.frame_sock,
            fps=self.fps,
            analytics=self.analytics,
        )

    def _control_setup(self):
        self.control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.control_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.control_sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.control_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
        self.control_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
        self.control_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)

        self.control_sock.bind(self.local_addr)

    def _frame_setup(self):
        self.frame_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.frame_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.frame_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 131072)

        self.frame_sock.bind(self.local_addr)

    def start(self):
        self.RUN = True

        self.control_thread = Thread(target=self.control_handler)
        self.control_thread.start()
        time.sleep(10)

    def stop(self, sig=None, farme=None):
        self.LOCK.acquire()
        self.RUN = False
        self.LOCK.release()
        self.cam.release()
        self.frame_sock.close()
        self.control_sock.close()
        self.control_thread.join()  # TEMP

    def join_threads(self):
        self.capture_thread.join()
        self.control_thread.join()

    def control_handler(self):
        print("started control thread")
        self.control_sock.listen(5)
        while self.RUN:
            self.handle_requests()

    def handle_requests(self):
        print("starting handle_requests")
        while self.RUN:
            # TODO: add logs
            sock, addr = self.control_sock.accept()

            try:
                data = self._recv_data(sock)
            except Exception as ex:
                # TODO: add logs traceback
                break

            header = str(data).split("|")[0]
            data = data[len(header) + 1 :]
            if header == "FPMA":
                self.handle_FPMA_request(data)
            elif header == "SVCS":
                self.start_capture()

        print("Exit handle_request")

    def handle_FPMA_request(self, data):
        self.LOCK.acquire()
        self.analytics.set_packets_received = int(data.decode().split("|")[0])
        self.analytics.set_frames_received = int(data.decode().split("|")[1])
        # TODO: change print to logs
        print(self.analytics.to_string())
        self.analytics.reset()
        self.LOCK.release()

    def _recv_data(self, sock):
        # TODO: add logs
        return sock.recv(4096)

    def start_capture(self):
        self.capture_thread = Thread(target=self._capture)
        self.capture_thread.start()

    def _capture(self):
        """captures video from the camera

        :param fps: how many frames per second the camera will capture
        :type fps: int
        :param res_h: height of the frame
        :type res_h: int
        :param res_w: width of the frame
        :type res_w: int
        """
        print("started capture thread")
        while self.RUN:
            _, frame = self.cam.read()
            _, data = self.encode_frame(frame)
            data = Data(data)
            self.agent.send_data(data, self.remote_addr)

    def encode_frame(self, frame):
        """compress frame to lower quailty and resize it

        :param frame: cv2 frame
        :type frame: np array
        """
        resized = cv2.resize(frame, (self.res_w, self.res_h), cv2.INTER_AREA)
        result, encoded_frame = cv2.imencode(".jpg", resized, self.encode_param)
        # return result, encoded_frame
        return result, encoded_frame.tobytes()

    def change_remote_address(self, addr):
        self.remote_addr = addr

    def is_connected(self):
        return self.connected


def logger_setup():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    log_file = logging.FileHandler("ServerService.log", "a", "utf-8")
    log_file.setLevel(logging.info)

    log_console = logging.StreamHandler()
    log_console.setLevel(logging.DEBUG)

    formatter = logging.Formatter("- %(name)s - %(ar%(levelname)-8s: %(message)s")


def main():
    print("Start Main")
    demo = ServerService()
    print("Server is ready")

    signal.signal(signal.SIGINT, demo.stop)

    print("Starting data")
    demo.start()

    try:
        demo.join_threads()
    except Exception as ex:
        demo.stop()
    print("Exit Main")


if __name__ == "__main__":
    main()
