import socket
import time

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
SLIDING_WINDOW_SIZE = 92

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
    previous_id = 0
    start_times = {}
    

    while not is_finished:
        messages = []
        current_pointer_id = window_pointer_id
        acks = {}

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
            
        for message_id, message in messages:
            start_delay = time.time()
            udp_socket.sendto(message, ('localhost', 5001))
            if message_id not in start_times:
                start_times[message_id] = start_delay

        while True:
            try:
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                end_delay = time.time()
                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big')

                if ack_id >= last_key > -1:
                    last_message = int.to_bytes(ack_id, SEQ_ID_SIZE, byteorder='big', signed=True) + b''
                    udp_socket.sendto(last_message, ('localhost', 5001))
                    last_ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                    fin, _ = udp_socket.recvfrom(PACKET_SIZE)
                    is_finished = True
                    break

                if ack_id != 0:
                    ack_id -= MESSAGE_SIZE

                acks[ack_id] = True

                while ack_id > previous_id:
                    previous_id += MESSAGE_SIZE
                    start_time = start_times.get(previous_id)
                    packet_delays.append(end_delay - start_time)

                    window_pointer_id += MESSAGE_SIZE

                if all(acks.values()):
                    start_times = {}
                    break
            except socket.timeout:
                print("timeout")
                for sid, message in messages:
                    if not acks[sid]:
                        window_pointer_id = sid
                        break
                break
                        
    end_time_tp = time.time()
    close_connection = int.to_bytes(-1, SEQ_ID_SIZE, byteorder='big', signed=True) + b'==FINACK=='
    udp_socket.sendto(close_connection, ('localhost', 5001))

    throughput = len(data) / (end_time_tp - start_time_tp)
    avg_packet_delay = sum(packet_delays) / len(packet_delays)

    print(f"{round(throughput, 2)},")
    print(f"{round(avg_packet_delay, 2)},")
    print(f"{round(throughput/avg_packet_delay, 2)}")
