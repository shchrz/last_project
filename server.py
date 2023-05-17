import cv2
import os
import socket
import logging, logging.handlers
import signal
import time
import keyboard
from threading import Thread, Lock
from protocol import Agent, Data, Analytics


os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"  # Insurance for camera release
logger = logging.getLogger(__name__)


class ServerService:
    def __init__(
        self, cam_id=0, fps=15, res_h=720, res_w=1280, compress_quailty=50, RUN=True
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
        self.lock = Lock()

        self.fps = fps
        self.frame_devider = round(30 / self.fps)
        print("devider: {}".format(self.frame_devider))
        self.res_w = res_w
        self.res_h = res_h

        self.agents = []

        self.local_addr = ("0.0.0.0", 20001)

        self.UDP_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.UDP_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.UDP_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 131072)
        self.UDP_sock.bind(self.local_addr)

        self.TCP_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.TCP_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.TCP_sock.bind(self.local_addr)

        self.FEC_flag = False
        self.SEC_flag = False

        self.analytics_thread = Thread(target=self.print_analytics)
        self.analytics_thread.start()

    def start(self):
        self.capture_thread = Thread(target=self.capture)
        self.capture_thread.start()

        self.start_listener()

    def start_listener(self):
        self.TCP_sock.listen(5)
        while self.RUN:
            try:
                client_sock, addr = self.TCP_sock.accept()
            except Exception:
                continue

            client_sock.setblocking(False)
            client_sock.send(str(addr[1]).encode())

            print("Client connected from {}".format(addr))
            print("{} Clients connected".format(len(self.agents) + 1))

            agent = Agent(self.UDP_sock, client_sock, addr, self.fps)

            self.lock.acquire()
            self.agents.append(agent)
            self.lock.release()

    def stop(self, sig=None, farme=None):
        print("Stopping")
        self.lock.acquire()
        self.RUN = False
        self.lock.release()
        time.sleep(0.5)
        self.cam.release()
        self.UDP_sock.close()
        self.TCP_sock.close()

        self.lock.acquire()
        while self.agents:
            self.agents.pop()
        self.lock.release()

        print("Stopped")

    def handle_client(self, agent):
        while self.RUN:
            pass

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
            if keyboard.is_pressed("q"):
                self.stop()
                continue

            if len(self.agents) == 0:
                continue
            _, frame = self.cam.read()
            index += 1
            if not index % self.frame_devider == 0:
                continue

            status, data = self.encode_frame(frame)
            if not status:
                continue
            data = Data(data)
            logger.info("Sending {}".format(data))
            for_remove = []
            for agent in self.agents:
                if not agent.is_alive():
                    for_remove.append(agent)
                agent.send_data(data.clone())

            if len(for_remove) > 0:
                self.lock.acquire()
                print("Removing agents: {}".format(for_remove))
                self.agents = [
                    agent for agent in self.agents if agent not in for_remove
                ]
                self.lock.release()

    def encode_frame(self, frame):
        """compress frame to lower quailty

        :param frame: cv2 frame
        :type frame: np array
        """
        try:
            resized = cv2.resize(frame, (self.res_w, self.res_h), cv2.INTER_AREA)

            _, encoded_frame = cv2.imencode(".jpg", resized, self.encode_param)
            #  tmp = cv2.imdecode(encoded_frame, 1)
            #  cv2.imshow("Preview Server", tmp)
            #  cv2.waitKey(1)
            return True, encoded_frame.tobytes()
        except Exception as ex:
            logger.exception("Error while resizing and encoding")

        return False, b""

    def print_analytics(self):
        sleep_time = 5.0
        while self.RUN:
            time.sleep(sleep_time)
            analytics = Analytics()
            for agent in self.agents:
                data = agent.get_analytics()
                analytics.add_frames_sent(data.get_frames_sent())
                analytics.add_packets_sent(data.get_packets_sent())
                data.reset()
            print(
                "Frame Per Second Send Overall: {}".format(
                    analytics.get_frames_sent() / sleep_time
                )
            )
            if len(self.agents) > 0:
                print(
                    "Frame Per Second Send Average: {}".format(
                        analytics.get_frames_sent() / sleep_time / len(self.agents)
                    )
                )
            print(
                "Packet Per Second Send Overall: {}".format(
                    analytics.get_packets_sent() / sleep_time
                )
            )
            if len(self.agents) > 0:
                print(
                    "Packet Per Second Send Average: {}".format(
                        analytics.get_packets_sent() / sleep_time / len(self.agents)
                    )
                )
            print(
                "Bitrate: {} Mbps".format(
                    analytics.get_bits_sent() / sleep_time / 1000000
                )
            )
            print("")
            analytics.reset()


def main():
    """
    sys.stdout = sys.__stdout__
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # add formatter to ch
    ch.setFormatter(formatter)

    fh_DEBUG = logging.handlers.RotatingFileHandler("server_debug.log")
    fh_DEBUG.setLevel(logging.DEBUG)

    fh_INFO = logging.handlers.RotatingFileHandler("server.log")
    fh_INFO.setLevel(logging.INFO)

    # add ch to logger
    logger.addHandler(ch)
    logger.addHandler(fh_DEBUG)
    logger.addHandler(fh_INFO)
    """

    demo = ServerService()

    signal.signal(signal.SIGINT, demo.stop)

    demo.start()


if __name__ == "__main__":
    main()
