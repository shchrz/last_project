import socket
import binascii
import time
import sys


CHUNK = 8192
COOKIE = 0x16f5f7a7
INDEX = 0


def check_cookie(data):
    return COOKIE == int.from_bytes(data[:4], byteorder="big", signed=False)

def check_CRC(data):
    CRC = int.from_bytes(data[4:8], byteorder="big", signed=False)
    return CRC == binascii.crc32(data[8:])

def client(addr, time_s):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.bind(("0.0.0.0", 20001))

    sock.sendto(b"START",(addr,20000))

    receive_frames(sock, time_s)

    msg = INDEX.to_bytes(4, byteorder="big", signed=False)

    sock.sendto(msg,(addr,20000))

def receive_frames(sock, time_s):
    global INDEX
    start_time = time.time()

    while float(time_s) >= time.time() - start_time:
        data =  sock.recvfrom(CHUNK)[0]
        if not check_cookie(data):
            continue
        if not check_CRC(data):
            continue
        INDEX += 1

    print("Chunks per second: ", INDEX / (time.time() - start_time))
    print("Frames Recevied: ", INDEX)

def server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
    sock.bind(("0.0.0.0", 20000))


    data, addr = sock.recvfrom(CHUNK)
    
    if data == b"START":
        send_frames(sock, addr)

def send_frames(sock, addr):
    global INDEX

    demo_data = b""
    for i in range(CHUNK-8):
        demo_data += b"1"

    demo = build_demo(demo_data)

    sock.setblocking(0)
    data = b""
    start_time = time.time()
    while True:
        try:
            data = sock.recvfrom(CHUNK)[0]
            if data:
                break
        except:
            sock.sendto(demo,addr)
            INDEX += 1

    data = int.from_bytes(data, byteorder="big", signed=False)

    print("Chunks per second: ", INDEX / (time.time() - start_time))
    print("Frames Sent: ", INDEX)
    print("Frames Recived: ", data)
    print("Precent of Frames Recived: ", (float(data)/INDEX)*100, "%")

def build_demo(data):
    CRC = binascii.crc32(data).to_bytes(4, byteorder="big", signed=False)
    demo = (COOKIE).to_bytes(4, byteorder="big", signed=False) + CRC + data
    return demo


if __name__ == "__main__":
    if sys.argv[1] == 'c':
        client(sys.argv[2],int(sys.argv[3]))
    if sys.argv[1] == 's':
        server()
