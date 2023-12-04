import socket
import time

# Sources:
# Haroon's 152 Reliable Sender code:
#   https://github.com/Haroon96/ecs152a-fall-2023/tree/main/week7/code

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
MAX_CWND = 100

cwnd = 1
sshthresh = 65536

class DuplicateAck(Exception):
    pass

with open('file.mp3', 'rb') as f:
    data = f.read()

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
    start_time_tp = time.time()
    udp_socket.bind(("0.0.0.0", 5000))
    udp_socket.settimeout(1)
    
    seq_id = 0
    packet_delays = []
    is_finished = False
    last_key = -1
    previous_id = 0
    duplicate_counter = 1

    while not is_finished:
        messages = []
        acks = {}
        start_times = {}
        seq_id_tmp = seq_id
        
        for i in range(cwnd):
            
            data_len = len(data[seq_id_tmp : seq_id_tmp + MESSAGE_SIZE])
            message = int.to_bytes(seq_id_tmp, SEQ_ID_SIZE, byteorder='big', signed=True) + data[seq_id_tmp : seq_id_tmp + MESSAGE_SIZE]
            if data_len < MESSAGE_SIZE:
                last_key = seq_id_tmp + data_len
                messages.append((last_key, message))
                break

            messages.append((seq_id_tmp, message))
            acks[seq_id_tmp] = False
            seq_id_tmp += MESSAGE_SIZE
        for message_id, message in messages:
            start_delay = time.time()
            udp_socket.sendto(message, ('localhost', 5001))
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
            
                ack_id -= MESSAGE_SIZE
                acks[ack_id] = True

                print(ack_id)
                

                # print(ack_id, ack[SEQ_ID_SIZE:])

                if ack_id == previous_id:
                    duplicate_counter += 1
                else:
                    previous_id = ack_id
                    packet_delays.append(end_delay - start_times.get(ack_id))
                    duplicate_counter = 1

                if duplicate_counter == 3:
                    duplicate_counter = 1
                    raise DuplicateAck("Recieved Triple acknowledgement")

                if all(acks.values()):
                    seq_id = ack_id + MESSAGE_SIZE
                    if cwnd < sshthresh:
                        cwnd *= 2
                    else:
                        cwnd += 2
                    break
                

            except socket.timeout:
                print("Timeout")
                for sid, message in messages:
                    if not acks[sid]:
                        udp_socket.sendto(message, ('localhost', 5001))
                        seq_id = sid
                        break
                sshthresh = int(cwnd/2)
                cwnd = 1
                print("SSH thresh is", sshthresh)
                break

            except DuplicateAck:
                print("Dup Ack")
                for sid, message in messages:
                    if not acks[sid]:
                        udp_socket.sendto(message, ('localhost', 5001))
                        seq_id = sid
                        break
                sshthresh = int(cwnd/2)
                cwnd = int(cwnd*0.7)
                break
        # print(cwnd)

    end_time_tp = time.time()
    close_connection = int.to_bytes(-1, SEQ_ID_SIZE, byteorder='big', signed=True) + b'==FINACK=='
    
    udp_socket.sendto(close_connection, ('localhost', 5001))

    throughput = len(data) / (end_time_tp - start_time_tp)
    avg_packet_delay = sum(packet_delays) / len(packet_delays)

    print(f"{round(throughput, 2)}, {round(avg_packet_delay, 2)}, {round(throughput/avg_packet_delay, 2)}")