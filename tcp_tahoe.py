import socket
import time

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE

cwnd = 1
sshthresh = 64


with open('send.txt', 'rb') as f:
    data = f.read()

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
    start_time_tp = time.time()
    udp_socket.bind(("0.0.0.0", 5000))
    udp_socket.settimeout(1)
    
    seq_id = 0
    packet_delays = []
    is_finished = False
    last_key = -1

    while is_finished == False:
        messages = []
        acks = {}
        seq_id_tmp = seq_id
        
        for i in range(cwnd):
            
            data_len = len(data[seq_id_tmp : seq_id_tmp + MESSAGE_SIZE])
            message = int.to_bytes(seq_id_tmp, SEQ_ID_SIZE, byteorder='big', signed=True) + data[seq_id_tmp : seq_id_tmp + MESSAGE_SIZE]
            if data_len < MESSAGE_SIZE:
                last_key = seq_id_tmp + data_len
                messages.append((last_key, message))
                # acks[last_key] = False
                break

            messages.append((seq_id_tmp, message))
            acks[seq_id_tmp] = False
            seq_id_tmp += MESSAGE_SIZE
        for _, message in messages:
            start_delay = time.time()
            udp_socket.sendto(message, ('localhost', 5001))
        
        while True:
            try:
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)

                end_delay = time.time()
                packet_delays.append(end_delay - start_delay)

                ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder='big')

                if ack_id >= last_key and last_key > -1:
                    # print(ack_id, ack[SEQ_ID_SIZE:])
                    last_message = int.to_bytes(ack_id, SEQ_ID_SIZE, byteorder='big', signed=True) + b''
                    udp_socket.sendto(last_message, ('localhost', 5001))
                    last_ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                    fin, _ = udp_socket.recvfrom(PACKET_SIZE)
                    is_finished = True
                    break
            
                ack_id -= MESSAGE_SIZE
                print(ack_id, ack[SEQ_ID_SIZE:])
                acks[ack_id] = True

                if all(acks.values()):
                    # time.sleep(1)
                    # print(ack_id, ack[SEQ_ID_SIZE:])
                    # print(acks)
                    seq_id = ack_id + MESSAGE_SIZE
                    if cwnd < sshthresh:
                        cwnd *= 2
                    else:
                        cwnd += 1
                    break
                

            except socket.timeout:
                for sid, message in messages:
                    if not acks[sid]:
                        print(f"ACK {(sid)} is duplicate")
                        udp_socket.sendto(message, ('localhost', 5001))
                        seq_id = sid
                        break
                sshthresh = cwnd/2
                print("SSHTHRESH is", sshthresh)
                cwnd = 1
                break
        print("CWND IS", cwnd)
    end_time_tp = time.time()
    # last_message = int.to_bytes(seq_id, SEQ_ID_SIZE, byteorder='big', signed=True) + b''
    close_connection = int.to_bytes(-1, SEQ_ID_SIZE, byteorder='big', signed=True) + b'==FINACK=='
    
    # udp_socket.sendto(last_message, ('localhost', 5001))
    # last_ack, _ = udp_socket.recvfrom(PACKET_SIZE)
    # fin, _ = udp_socket.recvfrom(PACKET_SIZE)
    
    udp_socket.sendto(close_connection, ('localhost', 5001))

    print(f"throughput: {len(data) / (end_time_tp - start_time_tp)} bytes per second")
    print(f"average delay per packet: {sum(packet_delays) / len(packet_delays)} seconds")