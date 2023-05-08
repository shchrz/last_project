import binascii
import logging

def send_to(sock, ip_port, data):
    """Sending data with size and CRC according to the protocol

    :param sock: socket to send from
    :type sock: socket.socket
    :param ip_port: address to send to
    :type ip_port: tuple(string, int)
    :param data: data to send
    :type data: bytes
    """
    size = len(data)
    tmp = data,binascii.crc32(data)
    CRC = binascii.crc32(data).to_bytes(4, byteorder="big", signed=False)

    data = size.to_bytes(4, byteorder="big", signed=False) + CRC + data
    sock.sendto(data[:8],ip_port)
    sock.sendto(data[8:round(len(data)/2)],ip_port)
    sock.sendto(data[round(len(data)/2):],ip_port)
    #sock.sendto(data[4096:],ip_port)

    index = 0
    while len(data) > index:
        sock.sendto(data[index:4096+index],ip_port)
        index += 20000

    #logging.info('1')
    logging.debug('Sent {} {} {} {}'.format(size.to_bytes(4, byteorder="big", signed=False),size, tmp[1], tmp[0]))

def receive_from(sock, CHUNK=4096):
    """Receiveing data by size according to the protocol

    :param sock: socket to receive from
    :type sock: socket.socket
    :return: tuple of packet source, CRC, and data
    :rtype: tuple(tuple(string, int), bytes, bytes)
    """
    data, addr = sock.recvfrom(8)
    
    CRC = int.from_bytes(data[4:8], byteorder="big", signed=False)
    size = int.from_bytes(data[:4], byteorder="big", signed=False)
    tmp = data[:4]
    print("size: ", size)

    data =  sock.recvfrom(round((len(data)-8)/2))[0]
    data += sock.recvfrom(len(data))[0]

    #data = data[7:]
   # while size > CHUNK:
       # data += sock.recvfrom(CHUNK)[0]
     #   size -= CHUNK

    #if size % CHUNK != 0:
     #   data += sock.recvfrom(CHUNK)[0]

    logging.debug('Recv {} {} {} {}'.format(tmp,size,CRC,data))
    return addr, CRC, data



