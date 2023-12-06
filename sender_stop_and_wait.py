import socket
import time

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE

with open('file.mp3', 'rb') as f:
    data = f.read()

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
    start_time_tp = time.time()
    udp_socket.bind(("0.0.0.0", 5000))
    udp_socket.settimeout(1)

    pointer_id = 0
    packet_delays = []

    while pointer_id < len(data):
        message = int.to_bytes(pointer_id, SEQ_ID_SIZE, byteorder='big', signed=True) +\
            data[pointer_id:pointer_id + MESSAGE_SIZE]

        start_delay = time.time()
        udp_socket.sendto(message, ('localhost', 5001))
        
        while True:
            try:
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                end_delay = time.time()
                packet_delays.append(end_delay - start_delay)
                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big')
                break

            except socket.timeout:
                udp_socket.sendto(message, ('localhost', 5001))

        pointer_id += MESSAGE_SIZE

    end_time_tp = time.time()
    close_connection = int.to_bytes(-1, SEQ_ID_SIZE, byteorder='big', signed=True) + b'==FINACK=='
    udp_socket.sendto(close_connection, ('localhost', 5001))

    throughput = len(data) / (end_time_tp - start_time_tp)
    avg_packet_delay = sum(packet_delays) / len(packet_delays)

    print(f"{round(throughput, 2)},")
    print(f"{round(avg_packet_delay, 2)},")
    print(f"{round(throughput/avg_packet_delay, 2)}")
