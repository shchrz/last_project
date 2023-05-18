import cv2
import os
import socket
import logging, logging.handlers
import signal
import time
import keyboard
from threading import Thread, Lock
from Crypto.Hash import SHA256
from protocol import Agent, Data, Analytics


os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"  # Insurance for camera release
logger = logging.getLogger(__name__)


class ServerService:
    def __init__(
        self,
        cam_id=0,
        fps=15,
        res_h=720,
        res_w=1280,
        compress_quality=50,
        RUN=True,
        FEC_Flag=False,
        SEC_False=False,
        password=None,
    ):
        """
        Initializes the ServerService class.

        Args:
            cam_id (int): Camera ID.
            fps (int): Frames per second.
            res_h (int): Frame height.
            res_w (int): Frame width.
            compress_quality (int): JPEG compression quality.
            RUN (bool): Flag indicating if the server is running.
            FEC_Flag (bool): Flag indicating if Forward Error Correction is enabled.
            SEC_False (bool): Flag indicating if Secure Communication is enabled.
            password (str): Password for secure communication.
        """
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        self.cam = cv2.VideoCapture(cam_id)
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.cam.set(cv2.CAP_PROP_FPS, 30)
        logger.info("Camera FPS: {}".format(self.cam.get(cv2.CAP_PROP_FPS)))

        self.encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), compress_quality]

        self.RUN = RUN
        self.lock = Lock()

        self.fps = fps
        self.frame_devider = round(30 / self.fps)
        logger.info("Frame Divider: {}".format(self.frame_devider))
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

        self.FEC_flag = FEC_Flag
        self.SEC_flag = SEC_False

        self.key = None

        if self.SEC_flag and password:
            self.key = SHA256.new(password.encode()).digest()
            logger.info("Key: {} (Length: {})".format(self.key, len(self.key)))

        self.analytics_thread = Thread(target=self.print_analytics)
        self.analytics_thread.start()

    def start(self):
        """
        Starts the server by launching capture thread and starting the listener.
        """
        self.capture_thread = Thread(target=self.capture)
        self.capture_thread.start()

        self.start_listener()

    def start_listener(self):
        """
        Starts the TCP listener to accept client connections.
        """
        self.TCP_sock.listen(5)
        while self.RUN:
            try:
                client_sock, addr = self.TCP_sock.accept()
            except Exception:
                continue

            client_sock.setblocking(False)
            client_sock.send(str(addr[1]).encode())

            logger.info("Client connected from {}".format(addr))
            logger.info("{} Clients connected".format(len(self.agents) + 1))

            agent = Agent(
                self.UDP_sock,
                client_sock,
                addr,
                fps=self.fps,
                FEC_flag=self.FEC_flag,
                key=self.key,
                SEC_flag=self.SEC_flag,
            )

            self.lock.acquire()
            self.agents.append(agent)
            self.lock.release()

    def stop(self, sig=None, frame=None):
        """
        Stops the server and releases resources.
        """
        logger.info("Stopping")
        self.lock.acquire()
        self.RUN = False
        self.lock.release()
        time.sleep(0.5)
        self.cam.release()
        self.UDP_sock.close()
        self.TCP_sock.close()

        self.lock.acquire()
        self.agents.clear()
        self.lock.release()

        logger.info("Stopped")

    def capture(self):
        """
        Captures video from the camera and sends frames to connected agents.
        """
        index = -1
        while self.RUN:
            if keyboard.is_pressed("q"):
                self.stop()
                continue

            if len(self.agents) == 0:
                continue

            try:
                _, frame = self.cam.read()
            except Exception as ex:
                logger.exception("Error while capturing frame from the camera")

            index += 1
            if not index % self.frame_devider == 0:
                continue

            status, data = self.encode_frame(frame)
            if not status:
                continue

            data = Data(data)
            logger.debug("Sending {}".format(data))
            for_remove = []
            for agent in self.agents:
                if not agent.is_alive():
                    for_remove.append(agent)
                try:
                    agent.send_data(data.clone())
                except Exception as ex:
                    logger.exception("Error while sending data to agent")

            if len(for_remove) > 0:
                self.lock.acquire()
                logger.info("Removing agents: {}".format(for_remove))
                self.agents = [
                    agent for agent in self.agents if agent not in for_remove
                ]
                self.lock.release()

    def encode_frame(self, frame):
        """
        Compresses the frame to lower quality.

        Args:
            frame (np.array): OpenCV frame.

        Returns:
            bool: Status indicating if encoding was successful.
            bytes: Encoded frame data.
        """
        try:
            resized = cv2.resize(frame, (self.res_w, self.res_h), cv2.INTER_AREA)
            _, encoded_frame = cv2.imencode(".jpg", resized, self.encode_param)
            return True, encoded_frame.tobytes()
        except Exception as ex:
            logger.exception("Error while resizing and encoding frame")
            return False, b""

    def print_analytics(self):
        """
        Prints analytics information such as frames sent, packets sent, and bitrate.
        """
        sleep_time = 5.0
        while self.RUN:
            time.sleep(sleep_time)
            analytics = Analytics()
            for agent in self.agents:
                try:
                    data = agent.get_analytics()
                    analytics.add_frames_sent(data.get_frames_sent())
                    analytics.add_packets_sent(data.get_packets_sent())
                    data.reset()
                except Exception as ex:
                    logger.exception("Error while retrieving agent analytics")

            logger.info(
                "Frames Per Second Sent Overall: {}".format(
                    analytics.get_frames_sent() / sleep_time
                )
            )
            if len(self.agents) > 0:
                logger.info(
                    "Frames Per Second Sent Average: {}".format(
                        analytics.get_frames_sent() / sleep_time / len(self.agents)
                    )
                )
            logger.info(
                "Packets Per Second Sent Overall: {}".format(
                    analytics.get_packets_sent() / sleep_time
                )
            )
            if len(self.agents) > 0:
                logger.info(
                    "Packets Per Second Sent Average: {}".format(
                        analytics.get_packets_sent() / sleep_time / len(self.agents)
                    )
                )
            logger.info(
                "Bitrate: {} Mbps".format(
                    analytics.get_bits_sent() / sleep_time / 1000000
                )
            )
            logger.info("")
            analytics.reset()


def main():
    demo = ServerService(password="123456")

    signal.signal(signal.SIGINT, demo.stop)

    demo.start()


if __name__ == "__main__":
    main()
