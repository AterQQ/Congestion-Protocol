import socket
import time
import statistics

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE

cwnd = 1
sshthresh = 64
timeout_time = 1

class TripleDuplicateAck(Exception):
    pass

with open('file.mp3', 'rb') as f:
    data = f.read()

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
    start_time_tp = time.time()
    udp_socket.bind(("0.0.0.0", 5000))
    udp_socket.settimeout(timeout_time)

    seq_id = 0
    prev_id = 0
    packet_delays = []
    is_finished = False
    last_key = -1
    start_times = {}
    duplicated_ack = 0

    while not is_finished:
        
        messages = []
        acks = {}
        seq_id_tmp = seq_id
        timeout_occured = False
        duplicated_ack_occured = False

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
            if message_id not in start_times:
                start_times[message_id] = start_delay

        while True:
            try:
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                end_delay = time.time()
                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big')

                if ack_id >= last_key and last_key > -1:
                    last_message = int.to_bytes(ack_id, SEQ_ID_SIZE, byteorder='big', signed=True) + b''
                    udp_socket.sendto(last_message, ('localhost', 5001))
                    last_ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                    fin, _ = udp_socket.recvfrom(PACKET_SIZE)
                    is_finished = True
                    break
                
                ack_id -= MESSAGE_SIZE
                acks[ack_id] = True
            
                if ack_id == prev_id:
                    duplicated_ack += 1
                else:
                    while ack_id > prev_id:
                        prev_id += MESSAGE_SIZE
                        start_time = start_times.get(prev_id)
                        packet_delays.append(end_delay - start_time)
                        seq_id += MESSAGE_SIZE
                        duplicated_ack = 1
                    
                if duplicated_ack == 3:
                    duplicated_ack = 1
                    raise TripleDuplicateAck("3 duplicated ACK detected")

                if all(acks.values()):
                    start_times = {}
                    break

            except socket.timeout:
                timeout_time = statistics.mean(packet_delays) + 3*statistics.stdev(packet_delays)
                udp_socket.settimeout(timeout_time)
                timeout_occured = True
                for sid, message in messages:
                    if not acks[sid]:
                        seq_id = sid
                        break
                break

            except TripleDuplicateAck:
                duplicated_ack_occured = True
                for sid, message in messages:
                    if not acks[sid]:
                        seq_id = sid
                        break
                break     

        if timeout_occured:
            sshthresh = cwnd/2
            cwnd = 1
        elif duplicated_ack_occured:
            sshthresh = cwnd/2
            cwnd = sshthresh
        else: 
            if cwnd < sshthresh:
                cwnd *= 2
            else:
                cwnd += 1
    
    end_time_tp = time.time()
    close_connection = int.to_bytes(-1, SEQ_ID_SIZE, byteorder='big', signed=True) + b'==FINACK=='

    udp_socket.sendto(close_connection, ('localhost', 5001))

    throughput = len(data) / (end_time_tp - start_time_tp)
    avg_packet_delay = sum(packet_delays) / len(packet_delays)

    print(f"{round(throughput, 2)},")
    print(f"{round(avg_packet_delay, 2)},")
    print(f"{round(throughput/avg_packet_delay, 2)}")