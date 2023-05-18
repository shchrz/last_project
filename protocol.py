import binascii
import time
import logging
import socket
import numpy as np

from threading import Lock
from Crypto.Cipher import ChaCha20
from Crypto.Random import get_random_bytes
from constents import *


class Analytics:
    def __init__(self):
        """
        Initializes an Analytics object with default values for all counters.
        """
        self.reset()

    def reset(self):
        """
        Resets all the counters to their default values.
        """
        self.packets_sent = 0
        self.packets_received = 0
        self.packets_CRC_error = 0
        self.frames_sent = 0
        self.frames_received = 0
        self.good_frames = 0
        self.init_time = time.time()

    def add_packets_sent(self, amount=1):
        """
        Increases the number of packets sent by the specified amount.

        Args:
            amount (int): The amount to increment the packets sent counter by. Default is 1.
        """
        self.packets_sent += amount

    def add_packets_received(self, amount=1):
        """
        Increases the number of packets received by the specified amount.

        Args:
            amount (int): The amount to increment the packets received counter by. Default is 1.
        """
        self.packets_received += amount

    def set_packets_received(self, amount):
        """
        Sets the number of packets received to the specified amount.

        Args:
            amount (int): The new value for the packets received counter.
        """
        self.packets_received = amount

    def add_packets_CRC_error(self, amount=1):
        """
        Increases the number of packets with CRC errors by the specified amount.

        Args:
            amount (int): The amount to increment the packets CRC error counter by. Default is 1.
        """
        self.packets_CRC_error += amount

    def add_frames_sent(self, amount=1):
        """
        Increases the number of frames sent by the specified amount.

        Args:
            amount (int): The amount to increment the frames sent counter by. Default is 1.
        """
        self.frames_sent += amount

    def add_frames_received(self, amount=1):
        """
        Increases the number of frames received by the specified amount.

        Args:
            amount (int): The amount to increment the frames received counter by. Default is 1.
        """
        self.frames_received += amount

    def add_good_frames(self, amount=1):
        """
        Increases the number of frames that are considered "good" by the specified amount.

        Args:
            amount (int): The amount to increment the good frames counter by. Default is 1.
        """
        self.good_frames += amount

    def set_frames_received(self, amount):
        """
        Sets the number of frames received to the specified amount.

        Args:
            amount (int): The new value for the frames received counter.
        """
        self.frames_received = amount

    def get_packets_sent(self) -> int:
        """
        Returns the number of packets sent.

        Returns:
            int: The number of packets sent.
        """
        return self.packets_sent

    def get_packets_received(self) -> int:
        """
        Returns the number of packets received.

        Returns:
            int: The number of packets received.
        """
        return self.packets_received

    def get_frames_sent(self) -> int:
        """
        Returns the number of frames sent.

        Returns:
            int: The number of frames sent.
        """
        return self.frames_sent

    def get_frames_received(self) -> int:
        """
        Returns the number of frames received.

        Returns:
            int: The number of frames received.
        """
        return self.frames_received

    def get_good_frames(self) -> int:
        """
        Returns the number of frames that are considered "good".

        Returns:
            int: The number of good frames.
        """
        return self.good_frames

    def get_packet_CRC(self):
        """
        Returns the number of packets with CRC errors.

        Returns:
            int: The number of packets with CRC errors.
        """
        return self.packets_CRC_error

    def get_packet_lost(self):
        """
        Calculates the percentage of packets lost.

        Returns:
            float: The percentage of packets lost.
        """
        return float(self.packets_received) / self.packets_sent * 100

    def get_packet_CRC_error(self):
        """
        Calculates the percentage of packets with CRC errors.

        Returns:
            float: The percentage of packets with CRC errors.
        """
        return (
            (float(self.packets_CRC_error) / self.packets_received * 100)
            if self.packets_CRC_error != 0
            else 0
        )

    def get_frame_lost(self):
        """
        Calculates the percentage of frames lost.

        Returns:
            float: The percentage of frames lost.
        """
        return float(self.frames_received) / self.frames_sent * 100

    def get_bits_sent(self):
        """
        Calculates the number of bits sent.

        Returns:
            int: The number of bits sent.
        """
        return self.packets_sent * PACKET_SIZE * 8

    def get_bits_received(self):
        """
        Calculates the number of bits received.

        Returns:
            int: The number of bits received.
        """
        return self.packets_received * PACKET_SIZE * 8

    def get_bitrate(self):
        """
        Calculates the bitrate in Mbit/s.

        Returns:
            float: The bitrate in Mbit/s.
        """
        return (
            float(self.packets_sent * PACKET_SIZE * 8)
            / (time.time() - self.init_time)
            / 1000000
        )

    def get_received_framerate(self):
        """
        Calculates the received frames per second (FPS).

        Returns:
            float: The received frames per second (FPS).
        """
        return float(self.frames_received) / (time.time() - self.init_time)

    def get_sent_framerate(self):
        """
        Calculates the sent frames per second (FPS).

        Returns:
            float: The sent frames per second (FPS).
        """
        return float(self.frames_sent) / (time.time() - self.init_time)

    def to_string(self) -> str:
        """
        Converts the analytics data to a formatted string.

        Returns:
            str: The formatted string representation of the analytics data.
        """
        return "Packet Loss: {:.2f}%, Frame Loss: {:.2f}%, Bitrate: {:.2f} Mbit/s, Received FPS: {:.2f}, Sent FPS: {:.2f}".format(
            self.get_packet_lost(),
            self.get_frame_lost(),
            self.get_bitrate(),
            self.get_received_framerate(),
            self.get_sent_framerate(),
        )

    def __str__(self) -> str:
        """
        Returns a string representation of the analytics data.

        Returns:
            str: The string representation of the analytics data.
        """
        return self.to_string()


class Packet:
    def __init__(self, param):
        """
        Initializes a Packet object.

        Args:
            param: The packet data to initialize the object.
                   If it's a tuple, it represents the packet parameters.
                   If it's a bytearray, it represents the raw packet data to decode.
        """
        try:
            if isinstance(param, tuple):
                self.Cookie = COOKIE
                self.CRC = np.uint32()
                self.Flags = {
                    "Version": VERSION_1_FLAG,
                    "Chunk_Flag": param[0],
                    "FEC_Flag": param[1],
                    "SEC_Flag": param[2],
                }
                self.Index = param[3]
                self.Serial = param[4]
                self.Data_Length = param[5]
                self.Payload_Length = param[6]
                self.Payload = param[7]
                self.Data = param[8]
                self.Raw = bytearray(PACKET_SIZE)
                self.encode()
            else:
                self.Cookie = np.uint32()
                self.CRC = np.uint32()
                self.Flags = {
                    "Version": np.uint8(),
                    "Chunk_Flag": np.uint8(),
                    "FEC_Flag": np.uint8(),
                    "SEC_Flag": np.uint8(),
                }
                self.Index = np.uint8()
                self.Serial = np.uint16()
                self.Data_Length = np.uint16()
                self.Payload_Length = np.uint16()
                self.Payload = str()
                self.Data = bytes()
                self.Raw = param
                self.decode()
        except Exception as e:
            logging.exception("Exception occurred while initializing Packet")

    def encode(self) -> None:
        """
        Encodes the packet object and updates the Raw packet data.
        """
        try:
            written_bytes = HEADER_SIZE

            self.Raw[written_bytes : written_bytes + FLAGS_SIZE] = (
                np.bitwise_or(  # Flags
                    np.bitwise_or(self.Flags["Version"], self.Flags["Chunk_Flag"]),
                    np.bitwise_or(self.Flags["FEC_Flag"], self.Flags["SEC_Flag"]),
                )
            ).tobytes()

            written_bytes += FLAGS_SIZE
            self.Raw[
                written_bytes : written_bytes + INDEX_SIZE
            ] = self.Index.tobytes()  # Index

            written_bytes += INDEX_SIZE
            self.Raw[
                written_bytes : written_bytes + SERIAL_SIZE
            ] = self.Serial.tobytes()  # Serial

            written_bytes += SERIAL_SIZE
            self.Raw[
                written_bytes : written_bytes + DATA_LENGTH_SIZE
            ] = self.Data_Length.tobytes()  # Data Length

            written_bytes += DATA_LENGTH_SIZE
            self.Raw[
                written_bytes : written_bytes + PAYLOAD_LENGTH_SIZE
            ] = self.Payload_Length.tobytes()  # Payload Length

            written_bytes += PAYLOAD_LENGTH_SIZE
            if self.Payload:
                self.Raw[
                    written_bytes : written_bytes + self.Payload_Length
                ] = self.Payload.encode()

            written_bytes += self.Payload_Length
            self.Raw[written_bytes : written_bytes + self.Data_Length] = self.Data

            self.Raw[:COOKIE_SIZE] = self.Cookie.tobytes()  # Cookie

            self.CRC = np.uint32(binascii.crc32(self.Raw[HEADER_SIZE:]))
            self.Raw[COOKIE_SIZE : COOKIE_SIZE + CRC_SIZE] = self.CRC.tobytes()  # CRC
        except Exception as e:
            logging.exception("Exception occurred while encoding the packet")

    def decode(self) -> None:
        """
        Decodes the raw packet data and updates the Packet object.
        """
        try:
            if self.Raw == b"":
                return

            read_bytes = 0
            self.Cookie = np.frombuffer(self.Raw[:COOKIE_SIZE], dtype=np.uint32)[0]

            read_bytes += COOKIE_SIZE
            self.CRC = np.frombuffer(
                self.Raw[read_bytes : read_bytes + CRC_SIZE], dtype=np.uint32
            )[0]

            read_bytes += CRC_SIZE
            flags = np.frombuffer(
                self.Raw[read_bytes : read_bytes + FLAGS_SIZE], dtype=np.uint8
            )
            self.Flags["Version"] = np.bitwise_and(flags, np.uint8(0b11110000))
            self.Flags["Chunk_Flag"] = np.bitwise_and(flags, np.uint8(0b00001100))
            self.Flags["FEC_Flag"] = np.bitwise_and(flags, np.uint8(0b00000010))
            self.Flags["SEC_Flag"] = np.bitwise_and(flags, np.uint8(0b00000001))

            read_bytes += FLAGS_SIZE
            self.Index = np.frombuffer(
                self.Raw[read_bytes : read_bytes + INDEX_SIZE], dtype=np.uint8
            )[0]

            read_bytes += INDEX_SIZE
            self.Serial = np.frombuffer(
                self.Raw[read_bytes : read_bytes + SERIAL_SIZE], dtype=np.uint16
            )[0]

            read_bytes += SERIAL_SIZE
            self.Data_Length = np.frombuffer(
                self.Raw[read_bytes : read_bytes + DATA_LENGTH_SIZE], dtype=np.uint16
            )[0]

            read_bytes += DATA_LENGTH_SIZE
            self.Payload_Length = np.frombuffer(
                self.Raw[read_bytes : read_bytes + PAYLOAD_LENGTH_SIZE], dtype=np.uint16
            )[0]

            read_bytes += PAYLOAD_LENGTH_SIZE
            self.Payload = self.Raw[
                read_bytes : read_bytes + self.Payload_Length
            ].decode()

            read_bytes += self.Payload_Length
            self.Data = self.Raw[read_bytes : read_bytes + self.Data_Length]
        except Exception as e:
            logging.exception("Exception occurred while decoding the packet")

    def check_cookie(self) -> bool:
        """
        Checks if the packet's Cookie is valid.

        Returns:
            bool: True if the Cookie is valid, False otherwise.
        """
        try:
            return self.Cookie == COOKIE
        except Exception as e:
            logging.exception("Exception occurred while checking the packet's Cookie")
            return False

    def check_CRC(self) -> bool:
        """
        Checks if the packet's CRC is valid.

        Returns:
            bool: True if the CRC is valid, False otherwise.
        """
        try:
            return self.CRC == binascii.crc32(self.Raw[HEADER_SIZE:])
        except Exception as e:
            logging.exception("Exception occurred while checking the packet's CRC")
            return False

    def is_last(self) -> bool:
        """
        Checks if the packet is the last chunk.

        Returns:
            bool: True if it's the last chunk, False otherwise.
        """
        try:
            return self.Flags["Chunk_Flag"] == CHUNK_LAST_FLAG
        except Exception as e:
            logging.exception(
                "Exception occurred while checking if the packet is the last chunk"
            )
            return False

    def is_valid(self) -> bool:
        """
        Checks if the packet is valid by verifying the Cookie and CRC.

        Returns:
            bool: True if the packet is valid, False otherwise.
        """
        try:
            return self.check_cookie() and self.check_CRC()
        except Exception as e:
            logging.exception("Exception occurred while checking the packet's validity")
            return False

    def get_serial(self) -> np.uint16:
        """
        Retrieves the serial number of the packet.

        Returns:
            np.uint16: The serial number.
        """
        try:
            return self.Serial
        except Exception as e:
            logging.exception(
                "Exception occurred while getting the packet's serial number"
            )

    def get_index(self) -> np.uint8:
        """
        Retrieves the index of the packet.

        Returns:
            np.uint8: The packet index.
        """
        try:
            return self.Index
        except Exception as e:
            logging.exception("Exception occurred while getting the packet's index")

    def get_payload(self) -> str:
        """
        Retrieves the payload of the packet.

        Returns:
            str: The packet payload.
        """
        try:
            return self.Payload
        except Exception as e:
            logging.exception("Exception occurred while getting the packet's payload")

    def update_data(self, data):
        """
        Updates the data of the packet.

        Args:
            data: The new data to update the packet with.
        """
        try:
            self.data = data
        except Exception as e:
            logging.exception("Exception occurred while updating the packet's data")

    def get_raw(self):
        """
        Retrieves the raw packet data.

        Returns:
            bytearray: The raw packet data.
        """
        try:
            return self.Raw
        except Exception as e:
            logging.exception("Exception occurred while getting the packet's raw data")

    def get_data(self):
        """
        Retrieves the data of the packet.

        Returns:
            bytes: The packet data.
        """
        try:
            return self.Data
        except Exception as e:
            logging.exception("Exception occurred while getting the packet's data")

    def is_SEC(self):
        """
        Checks if the packet has the SEC (Secure) flag.

        Returns:
            bool: True if the SEC flag is set, False otherwise.
        """
        try:
            return self.Flags["SEC_Flag"] == SEC_ON_FLAG
        except Exception as e:
            logging.exception(
                "Exception occurred while checking if the packet has the SEC flag"
            )

    def __str__(self) -> str:
        """
        Returns a string representation of the Packet object.

        Returns:
            str: The string representation of the Packet.
        """
        try:
            return "{}...{}".format(str(self.Raw[:16]), str(self.Raw[-17:]))
        except Exception as e:
            logging.exception(
                "Exception occurred while converting the Packet to a string"
            )
            return ""


class Data:
    def __init__(self, data):
        """
        Initializes a Data object.

        Args:
            data: The raw data.
        """
        self.raw = data
        self.pointer = 0
        self.end = False
        self.size = len(data)
        if self.size > 0:
            self.CRC = np.uint32(binascii.crc32(data))

    def get_data_chunk(self, size):
        """
        Retrieves a chunk of data from the current position.

        Args:
            size: The size of the chunk to retrieve.

        Returns:
            The sliced data chunk.
        """
        sliced_data = self.raw[self.pointer : self.pointer + size]
        self.move_pointer(size)
        return sliced_data

    def move_pointer(self, amount):
        """
        Moves the pointer forward by the specified amount.

        Args:
            amount: The amount to move the pointer by.
        """
        self.pointer += amount

        if self.pointer >= self.size:
            self.end = True

    def amount_to_end(self):
        """
        Calculates the amount of data remaining until the end.

        Returns:
            The amount of data remaining until the end.
        """
        return self.size - self.pointer

    def is_end(self):
        """
        Checks if the end of the data has been reached.

        Returns:
            True if the end has been reached, False otherwise.
        """
        return self.end

    def get_CRC(self):
        """
        Retrieves the CRC value of the data.

        Returns:
            The CRC value.
        """
        return self.CRC

    def get_data(self):
        """
        Retrieves the raw data.

        Returns:
            The raw data.
        """
        return self.raw

    def get_size(self):
        """
        Retrieves the size of the data.

        Returns:
            The size of the data.
        """
        return self.size

    def clone(self):
        """
        Creates a clone of the Data object.

        Returns:
            A new Data object with the same raw data.
        """
        return Data(self.raw)

    def __str__(self) -> str:
        """
        Returns a string representation of the Data object.

        Returns:
            A string representation of the Data object.
        """
        return "{}...{}".format(str(self.raw[:16]), str(self.raw[-17:]))


class PacketList:
    def __init__(self, packet: Packet) -> None:
        """
        Initializes a PacketList object.

        Args:
            packet (Packet): The initial packet to add to the list.
        """
        try:
            self.init_time = time.time()
            self.packets = dict()
            self.num_of_packets = -1
            self.add_packet(packet)
        except Exception as e:
            logging.exception("Exception occurred while initializing PacketList")

    def add_packet(self, packet: Packet):
        """
        Adds a packet to the packet list.

        Args:
            packet (Packet): The packet to add.
        """
        try:
            self.packets[str(packet.get_index())] = packet
            if packet.is_last():
                self.num_of_packets = int(packet.get_index()) + 1
        except Exception as e:
            logging.exception("Exception occurred while adding a packet to PacketList")

    def is_complete(self) -> bool:
        """
        Checks if the packet list is complete.

        Returns:
            bool: True if the packet list is complete, False otherwise.
        """
        try:
            if self.num_of_packets > -1:
                return self.num_of_packets == len(self.packets)
            return False
        except Exception as e:
            logging.exception(
                "Exception occurred while checking if PacketList is complete"
            )
            return False

    def get_packet(self, index):
        """
        Retrieves a packet from the packet list.

        Args:
            index: The index of the packet to retrieve.

        Returns:
            Packet: The requested packet.
        """
        try:
            return self.packets[index]
        except Exception as e:
            logging.exception(
                "Exception occurred while retrieving a packet from PacketList"
            )
            return None

    def get_init_time(self) -> float:
        """
        Retrieves the initialization time of the packet list.

        Returns:
            float: The initialization time.
        """
        try:
            return self.init_time
        except Exception as e:
            logging.exception(
                "Exception occurred while retrieving the initialization time of PacketList"
            )
            return 0.0

    def to_data(self):
        """
        Converts the packet list to a Data object.

        Returns:
            Data: The combined data from all packets in the list.
        """
        try:
            data = b""
            for i in range(self.num_of_packets):
                data += self.packets[str(i)].get_data()
            return Data(data)
        except Exception as e:
            logging.exception("Exception occurred while converting PacketList to Data")
            return Data(b"")


class Agent:
    def __init__(
        self,
        udp_sock,
        tcp_sock,
        addr,
        key=bytes(),
        fps=15,
        FEC_flag=FEC_OFF_FLAG,
        SEC_flag=SEC_OFF_FLAG,
    ):
        """
        Initializes an Agent instance.

        Args:
            udp_sock: UDP socket for sending/receiving packets.
            tcp_sock: TCP socket for checking if the connection is closed.
            addr: Address of the remote endpoint.
            key: Encryption key (optional).
            fps: Frames per second (optional).
            FEC_flag: Forward Error Correction flag (optional).
            SEC_flag: Secure flag (optional).
        """
        self.FEC_flag = FEC_flag
        self.SEC_flag = SEC_flag
        self.data_serial = np.uint16(0)
        self.RUN = False
        self.udp_sock = udp_sock
        self.tcp_sock = tcp_sock
        self.addr = addr
        self.fps = fps
        self.data_dict = dict()
        self.lock = Lock()
        self.analytics = Analytics()
        self.key = key

    def is_tcp_socket_closed(self) -> bool:
        """
        Checks if the TCP socket is closed.

        Returns:
            True if the socket is closed, False otherwise.
        """
        try:
            data = self.tcp_sock.recv(16, socket.MSG_PEEK)
            if len(data) == 0:
                return True
        except BlockingIOError:
            return False
        except ConnectionResetError:
            return True
        except Exception as e:
            logging.exception(
                "Unexpected exception when checking if a socket is closed"
            )
            return False
        return False

    def is_alive(self) -> bool:
        """
        Checks if the agent is alive by checking if the TCP socket is closed.

        Returns:
            True if the agent is alive, False otherwise.
        """
        return not self.is_tcp_socket_closed()

    def send_data(self, data: Data):
        """
        Sends data to the remote endpoint.

        Args:
            data: Data to be sent.
        """
        try:
            self.analytics.add_frames_sent()
            index = np.uint8(0)
            while not data.is_end():
                self._send_packet(self._create_packet(index, data))
                index += np.uint8(1)
                time.sleep(0.001)
            self._increase_serial()
        except Exception as e:
            logging.exception("Exception occurred while sending data")

    def _increase_serial(self):
        """
        Increases the data serial number.
        """
        if self.data_serial == 65535:
            self.data_serial = np.uint16(0)
        self.data_serial += np.uint16(1)

    def _create_packet(self, index, data: Data):
        """
        Creates a packet for sending data.

        Args:
            index: Packet index.
            data: Data to be included in the packet.

        Returns:
            Created Packet object.
        """
        try:
            payload = str()
            payload_length = np.uint16(len(payload))
            chunk_flag = CHUNK_NORMAL_FLAG

            if index == 0:
                chunk_flag = CHUNK_FIRST_FLAG

            data_chunk_length = np.uint16(RAW_SIZE)

            if data.amount_to_end() < RAW_SIZE:
                chunk_flag = CHUNK_LAST_FLAG
                data_chunk_length = np.uint16(data.amount_to_end())

            ready_data = b""
            if self.SEC_flag == SEC_ON_FLAG:
                nonce = get_random_bytes(12)
                payload = (
                    str(np.frombuffer(nonce[:8], dtype=np.uint64)[0])
                    + "|"
                    + str(np.frombuffer(nonce[8:], dtype=np.uint32)[0])
                )
                payload_length = np.uint16(len(payload))

                if chunk_flag == CHUNK_LAST_FLAG:
                    data_chunk_length = np.uint16(data_chunk_length + payload_length)
                else:
                    data_chunk_length = np.uint16(data_chunk_length - payload_length)

                cipher = ChaCha20.new(key=self.key, nonce=nonce)
                ready_data = cipher.encrypt(data.get_data_chunk(data_chunk_length))

            else:
                ready_data = data.get_data_chunk(data_chunk_length)

            return Packet(
                (
                    chunk_flag,
                    self.FEC_flag,
                    self.SEC_flag,
                    index,
                    self.data_serial,
                    data_chunk_length,
                    payload_length,
                    payload,
                    ready_data,
                )
            )
        except Exception as e:
            logging.exception("Exception occurred while creating a packet")

    def _send_packet(self, packet: Packet):
        """
        Sends a packet to the remote endpoint.

        Args:
            packet: Packet to be sent.
        """
        try:
            self.udp_sock.sendto(packet.get_raw(), self.addr)
            self.analytics.add_packets_sent()
        except Exception as e:
            logging.exception("Exception occurred while sending a packet")

    def start_receive(self):
        """
        Starts receiving packets from the remote endpoint.
        """
        self.RUN = True
        while self.RUN:
            try:
                is_full, packet = self._receive_packet()
                if not is_full:
                    continue

                if not packet.is_valid():
                    self.analytics.add_packets_CRC_error()
                    continue

                if packet.is_SEC():
                    payload = packet.get_payload().split("|")
                    nonce = (
                        np.uint64(payload[0]).tobytes()
                        + np.uint32(payload[1]).tobytes()
                    )
                    cipher = ChaCha20.new(key=self.key, nonce=nonce)

                    decrypted = cipher.decrypt(packet.get_data())
                    packet.update_data(decrypted)

                serial = packet.get_serial()
                if str(serial) in self.data_dict:
                    self.data_dict[str(serial)].add_packet(packet)
                else:
                    self.data_dict[str(serial)] = PacketList(packet)
                    self.analytics.add_frames_received()
                    logging.debug("Added both")

                self._clean_up()
            except Exception as e:
                logging.exception("Exception occurred while receiving packets")

    def _clean_up(self):
        """
        Cleans up the data dictionary by removing expired entries.
        """
        current_time = time.time()
        for i in list(self.data_dict.keys()):
            if i not in self.data_dict:
                continue
            if current_time - self.data_dict[i].get_init_time() > TIMEOUT:
                self.lock.acquire()
                del self.data_dict[i]
                self.lock.release()

    def stop_receive(self):
        """
        Stops receiving packets.
        """
        self.RUN = False

    def _receive_packet(self):
        """
        Receives a packet from the UDP socket.

        Returns:
            Tuple containing a boolean indicating if a full packet was received and the received Packet object.
        """
        try:
            data = self.udp_sock.recvfrom(PACKET_SIZE)[0]
            self.analytics.add_packets_received()
            return True, Packet(data)
        except OSError:
            pass
        except Exception as ex:
            logging.exception("Exception occurred while receiving a packet")
        return False, Packet(b"")

    def get_last_data(self) -> tuple():
        """
        Retrieves the last complete data and its serial number.

        Returns:
            Tuple containing the last complete Data object and its serial number.
        """
        self.lock.acquire()
        completed = []
        for i in list(self.data_dict.keys()):
            if self.data_dict[i].is_complete():
                completed.append(int(i))

        self.lock.release()
        if not completed:
            return Data(b""), -1

        serial = max(completed)
        if serial <= self.data_serial:
            return Data(b""), -1

        self.analytics.add_good_frames()
        self.data_serial = serial
        return self.data_dict[str(self.data_serial)].to_data(), serial

    def get_analytics(self):
        """
        Retrieves the analytics data.

        Returns:
            Analytics object containing various statistics.
        """
        return self.analytics
