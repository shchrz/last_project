import binascii
import time
import logging
import numpy as np

from threading import Lock
from constents import *


class Packet:
    def __init__(self, param):
        if type(param) == tuple:
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

    def encode(self) -> None:
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

    def decode(self) -> None:
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
        self.Payload = self.Raw[read_bytes : read_bytes + self.Payload_Length].decode()

        read_bytes += self.Payload_Length
        self.Data = self.Raw[read_bytes : read_bytes + self.Data_Length]

    def check_cookie(self) -> bool:
        return self.Cookie == COOKIE

    def check_CRC(self) -> bool:
        return self.CRC == binascii.crc32(self.Raw[HEADER_SIZE:])

    def is_last(self) -> bool:
        return self.Flags["Chunk_Flag"] == CHUNK_LAST_FLAG

    def is_valid(self) -> bool:
        return self.check_cookie and self.check_CRC()

    def get_serial(self) -> np.uint16:
        return self.Serial

    def get_index(self) -> np.uint8:
        return self.Index

    def get_raw(self):
        return self.Raw

    def get_data(self):
        return self.Data

    def __str__(self) -> str:
        return "{}...{}".format(str(self.Raw[:16]), str(self.Raw[-17:]))


class Data:
    def __init__(self, data):
        self.raw = data
        self.pointer = 0
        self.end = False
        self.size = len(data)
        if self.size > 0:
            self.CRC = np.uint32(binascii.crc32(data))

    def get_data_chunk(self, size):
        sliced_data = self.raw[self.pointer : self.pointer + size]
        self.move_pointer(size)
        return sliced_data

    def move_pointer(self, amount):
        self.pointer += amount

        if self.pointer >= self.size:
            self.end = True
        # check if end

    def amount_to_end(self):
        return self.size - self.pointer

    def is_end(self):
        return self.end

    def get_CRC(self):
        return self.CRC

    def get_data(self):
        return self.raw

    def __str__(self) -> str:
        return "{}...{}".format(str(self.raw[:16]), str(self.raw[-17:]))


class PacketList:
    def __init__(self, packet: Packet) -> None:
        self.init_time = time.time()
        self.packets = dict()
        self.num_of_packets = -1  # Gets its value when last packet is received
        self.add_packet(packet)

    def add_packet(self, packet: Packet):
        self.packets[str(packet.get_index())] = packet
        if packet.is_last():
            self.num_of_packets = int(packet.get_index())

    def is_complete(self) -> bool:
        if self.num_of_packets > -1:
            return self.num_of_packets == len(self.packets) - 1
        return False

    def get_packet(self, index) -> Packet:
        return self.packets[index]

    def get_init_time(self) -> float:
        return self.init_time

    def to_data(self) -> Data:
        data = b""
        for i in range(self.num_of_packets):
            data += self.packets[str(i)].get_data()
        return Data(data)


class Agent:
    def __init__(self, sock, fps=15, FEC_flag=FEC_OFF_FLAG, SEC_flag=SEC_OFF_FLAG):
        self.FEC_flag = FEC_flag
        self.SEC_flag = SEC_flag
        self.data_serial = np.uint16(0)
        self.RUN = False
        self.sock = sock
        self.fps = fps
        self.data_dict = dict()
        self.lock = Lock()

    def send_data(self, data: Data, addr):  # Server-side
        logging.debug("Sending {} to {}".format(data, addr))
        self.addr = addr  # (ip,port)
        packet_spacing = 1.0 / (self.fps * PACKETS_PER_FARME)
        index = np.uint8(0)
        while not data.is_end():
            self._send_packet(self._create_packet(index, data))
            index += np.uint8(1)
            time.sleep(packet_spacing)
        self._increase_serial()

    def _increase_serial(self):
        if self.data_serial == 65535:
            self.data_serial = np.uint16(0)
        self.data_serial += np.uint16(1)
        # check max

    def _create_packet(self, index, data: Data):
        payload = str()
        payload_length = np.uint16(len(payload))
        chunk_flag = CHUNK_NORMAL_FLAG

        if index == 0:
            chunk_flag = CHUNK_FIRST_FLAG
            payload = str(data.get_CRC())
            payload_length = np.uint16(len(payload))

        data_chunk_length = np.uint16(RAW_SIZE - payload_length)

        if data.amount_to_end() < RAW_SIZE:
            chunk_flag = CHUNK_LAST_FLAG
            data_chunk_length = np.uint16(data.amount_to_end())

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
                data.get_data_chunk(data_chunk_length),
            )
        )

    def _send_packet(self, packet: Packet):  # Agent-side
        self.sock.sendto(packet.get_raw(), self.addr)

    def start_receive(self):
        # dict serials for keys and list/sets of packets orderby index
        self.RUN = True
        while self.RUN:
            packet = self._receive_packet()
            logging.debug("Received {}".format(packet))
            if not packet.is_valid():
                continue
            serial = packet.get_serial()
            if str(serial) in self.data_dict:
                logging.debug("Adding {} to {}".format(packet, serial))
                self.data_dict[str(serial)].add_packet(packet)
                logging.debug("Added")
            else:
                logging.debug(
                    "Adding {} with {} key to {}".format(packet, serial, self.data_dict)
                )
                self.data_dict[str(serial)] = PacketList(packet)
                logging.debug("Added both")

            self._clean_up()

    def _clean_up(self):
        current_time = time.time()
        for i in list(self.data_dict.keys()):  # iter(self.data_dict):
            if i not in self.data_dict:
                continue
            if current_time - self.data_dict[i].get_init_time() > TIMEOUT:
                self.lock.acquire()
                del self.data_dict[i]
                self.lock.release()

    def stop_receive(self):
        self.RUN = False

    def _receive_packet(self) -> Packet:  # Client-side
        # receive packet via sock
        data = self.sock.recvfrom(PACKET_SIZE)[0]
        return Packet(data)

    def get_last_data(self) -> Data:
        # return the data with the largest serial number
        self.lock.acquire()
        completed = []
        for i in list(self.data_dict.keys()):  # iter(self.data_dict):
            if self.data_dict[i].is_complete():
                completed.append(int(i))
        self.lock.release()
        if not completed:
            return Data(b"")

        serial = max(completed)
        if serial <= self.data_serial:
            return Data(b"")

        self.data_serial = serial
        return self.data_dict[str(self.data_serial)].to_data()
