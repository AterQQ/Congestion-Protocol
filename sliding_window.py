import socket
import time

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
SLIDING_WINDOW_SIZE = 100

with open('congestion_control_ecs152a/docker/file.mp3', 'rb') as f:
    data = f.read()

print(len(data))

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
    start_time_tp = time.time()
    udp_socket.bind(("0.0.0.0", 5000))
    udp_socket.settimeout(1)

    window_pointer_id = 0
    packet_delays = []
    while window_pointer_id < len(data):
        messages = []
        acks = {}
        current_pointer_id = window_pointer_id

        for i in range(SLIDING_WINDOW_SIZE):
            message = int.to_bytes(current_pointer_id, SEQ_ID_SIZE, byteorder='big', signed=True) + \
                      data[current_pointer_id:current_pointer_id + MESSAGE_SIZE]
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
                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big') - MESSAGE_SIZE
                print(ack_id, ack[SEQ_ID_SIZE:])
                acks[ack_id] = True

                if all(acks.values()) or len(data) == ack_id + MESSAGE_SIZE:
                    break
            except socket.timeout:
                print("timeout")
                for sid, message in messages:
                    if not acks[sid]:
                        udp_socket.sendto(message, ('localhost', 5001))

        window_pointer_id += MESSAGE_SIZE * SLIDING_WINDOW_SIZE

    end_time_tp = time.time()
    udp_socket.sendto(int.to_bytes(window_pointer_id, SEQ_ID_SIZE, byteorder='big', signed=True) + b'', ('localhost', 5001))

print(f"throughput: {len(data) / (end_time_tp - start_time_tp)} bytes per second")
print(f"average delay per packet: {sum(packet_delays) / len(packet_delays)} seconds")
