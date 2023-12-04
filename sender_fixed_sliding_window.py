import socket
import time

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
SLIDING_WINDOW_SIZE = 100

with open('file.mp3', 'rb') as f:
    data = f.read()

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
    start_time_tp = time.time()
    udp_socket.bind(("0.0.0.0", 5000))
    udp_socket.settimeout(1)

    window_pointer_id = 0
    packet_delays = []
    is_finished = False
    last_key = -1

    while not is_finished:
        messages = []
        acks = {}
        current_pointer_id = window_pointer_id

        for i in range(SLIDING_WINDOW_SIZE):
            data_len = len(data[current_pointer_id: current_pointer_id + MESSAGE_SIZE])
            message = int.to_bytes(current_pointer_id, SEQ_ID_SIZE, byteorder='big', signed=True) + \
                      data[current_pointer_id:current_pointer_id + MESSAGE_SIZE]
            if data_len < MESSAGE_SIZE:
                last_key = current_pointer_id + data_len
                messages.append((last_key, message))
                break
            messages.append((current_pointer_id, message))
            acks[current_pointer_id] = False
            current_pointer_id += MESSAGE_SIZE
        for _, message in messages:
            start_delay = time.time()
            udp_socket.sendto(message, ('localhost', 5001))

        while True:
            try:
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                end_delay = time.time()
                packet_delays.append(end_delay - start_delay)
                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big')

                if ack_id >= last_key > -1:
                    last_message = int.to_bytes(ack_id, SEQ_ID_SIZE, byteorder='big', signed=True) + b''
                    udp_socket.sendto(last_message, ('localhost', 5001))
                    last_ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                    fin, _ = udp_socket.recvfrom(PACKET_SIZE)
                    is_finished = True
                    break

                ack_id -= MESSAGE_SIZE
                print(ack_id, ack[SEQ_ID_SIZE:])
                acks[ack_id] = True
                window_pointer_id += MESSAGE_SIZE

                if all(acks.values()):
                    break
            except socket.timeout:
                print("timeout")
                for sid, message in messages:
                    if not acks[sid]:
                        udp_socket.sendto(message, ('localhost', 5001))


    end_time_tp = time.time()
    close_connection = int.to_bytes(-1, SEQ_ID_SIZE, byteorder='big', signed=True) + b'==FINACK=='
    udp_socket.sendto(close_connection, ('localhost', 5001))

print(f"throughput: {len(data) / (end_time_tp - start_time_tp)} bytes per second")
print(f"average delay per packet: {sum(packet_delays) / len(packet_delays)} seconds")
print(f'{round((len(data) / (end_time_tp - start_time_tp)) / (sum(packet_delays) / len(packet_delays)), 2)}')
