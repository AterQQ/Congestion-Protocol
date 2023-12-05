import socket
import time

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE

cwnd = 1
sshthresh = 64
TIMEOUT_TIME = 1

class TripleDuplicateAck(Exception):
    def __init__(self, message=None):
        self.message = messages
        super().__init__(message)

with open('file.mp3', 'rb') as f:
    data = f.read()

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
    start_time_tp = time.time()
    udp_socket.bind(("0.0.0.0", 5000))
    udp_socket.settimeout(TIMEOUT_TIME)

    seq_id = 0
    prev_id = 0
    packet_delays = []
    is_finished = False
    last_key = -1
    duplicated_ack = 0

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

                # Last message is sent, exit logic
                if ack_id >= last_key and last_key > -1:
                    last_message = int.to_bytes(ack_id, SEQ_ID_SIZE, byteorder='big', signed=True) + b''
                    udp_socket.sendto(last_message, ('localhost', 5001))
                    last_ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                    fin, _ = udp_socket.recvfrom(PACKET_SIZE)
                    is_finished = True
                    break

                
                ack_id -= MESSAGE_SIZE
                acks[ack_id] = True
            
                print(ack_id)

                # Check if there is duplicated ACK
                if ack_id == prev_id:
                    duplicated_ack += 1
                else:
                    prev_id = ack_id
                    packet_delays.append(end_delay - start_times.get(ack_id))
                

                if duplicated_ack == 3:
                    duplicated_ack = 0
                    raise TripleDuplicateAck("3 duplicated ACK detected")

                if all(acks.values()):
                    seq_id = ack_id + MESSAGE_SIZE
                    if cwnd < sshthresh:
                        cwnd *= 2
                    else:
                        cwnd += 1
                    break

            except socket.timeout:
                print("timeout")
                for sid, message in messages:
                    if not acks[sid]:
                        udp_socket.sendto(message, ('localhost', 5001))
                        seq_id = sid
                        prev_id = sid - MESSAGE_SIZE
                        break
                sshthresh = int(cwnd/2)
                print("SSHTHRESH is", sshthresh)
                cwnd = 1
                break

            except TripleDuplicateAck:
                print("Tripe duplicated ACK")
                for sid, message in messages:
                    if not acks[sid]:
                        udp_socket.sendto(message, ('localhost',  5001))
                        seq_id = sid
                        break
                sshthresh = int(cwnd/2)
                cwnd = sshthresh
                break

        print("CWND IS", cwnd)
    end_time_tp = time.time()

    close_connection = int.to_bytes(-1, SEQ_ID_SIZE, byteorder='big', signed=True) + b'==FINACK=='

    udp_socket.sendto(close_connection, ('localhost', 5001))

    throughput = len(data) / (end_time_tp - start_time_tp)
    avg_packet_delay = sum(packet_delays) / len(packet_delays)

    print(f"throughput: {round(throughput, 2)}")
    print(f"average delay: {round(avg_packet_delay, 2)}")
    print(f"throughput / average delay: {round(throughput/avg_packet_delay, 2)}")