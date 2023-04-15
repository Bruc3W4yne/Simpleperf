import socket
import sys
import argparse
import time
import threading


def serverSide(bindAdress, port, format, interval, buffer_size=1000):
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    #Bind socket to provided IP and Port
    serverSocket.bind((bindAdress, port))

    #Start listening for connections
    serverSocket.listen(1)

    print(f"A simpleperf server is listening on port {port}")

    while True:
        clientSocket, clientAddress = serverSocket.accept()
        print(f"A simpleperf Client with {clientAddress[0]}:{clientAddress[1]} is connected with {bindAdress}:{port}")

        start_time = time.time()
        bytes_received = 0
        interval_bytes = 0
        prev_bytes = 0
        interval_count = interval

        while True:
            data = clientSocket.recv(buffer_size)
            bytes_received += len(data)
            transfer_mb = bytes_received / (1024 * 1024)

            if b"BYE" not in data and interval is not None:
                elapsed_time = time.time() - start_time
                if elapsed_time >= interval_count:
                    interval_start = elapsed_time - interval
                    interval_stop = elapsed_time
                    interval_bytes = transfer_mb - prev_bytes
                    prev_bytes = transfer_mb
                    formattedResults("Server", clientAddress[0], clientAddress[1], interval_bytes, interval_start, interval_stop, format, interval)
                    interval_count += interval

            elif b"BYE" in data:
                duration = time.time() - start_time
                clientSocket.sendall(b"ACK : BYE")
                formattedResults("Server", clientAddress[0], clientAddress[1], transfer_mb, 0, duration, format, duration)
                break

        clientSocket.close()


def clientSide(local_ip, local_port, server_ip, port, duration, format, interval, num, buffer_size=1000):
    print(f"A simpleperf client connecting to server <{server_ip}>, port {port}")

    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket.bind((local_ip, local_port))
    clientSocket.connect((server_ip, port))

    print(f"Client {local_ip}:{local_port} connected with {server_ip}, on port {port}")

    start_time = time.time()
    bytes_sent = 0
    data = bytes(buffer_size)

    if num is None:
        while time.time() - start_time < duration:
            clientSocket.sendall(data)
            bytes_sent += buffer_size
    else:
        while bytes_sent < num:
            clientSocket.sendall(data)
            bytes_sent += buffer_size

    clientSocket.sendall(b"BYE")
    ack = clientSocket.recv(buffer_size)

    if b"ACK : BYE" in ack:
        duration = time.time() - start_time
        transfer_mb = bytes_sent / (1024 * 1024)
        formattedResults("Client", server_ip, port, transfer_mb, 0, duration, format, duration)
        
    clientSocket.close()

def parseNum(num_str):
    if num_str.endswith("KB"):
        return int(num_str[:-2]) * 1024
    elif num_str.endswith("MB"):
        return int(num_str[:-2]) * 1024 * 1024
    else:
        return int(num_str)

def formattedResults(role, server_ip, port, transfer_mb, start, stop, format, interval):
    if format == "B":
        unit = "B"
        speed = "bps"
        transfer_mb *= 1024 * 1024
    elif format == "KB":
        unit = "KB"
        speed = "Kbps"
        transfer_mb *= 1024
    else:
        unit ="MB"
        speed = "Mbps"

    rate = (transfer_mb * 8) / interval

    if stop == interval:
        print("----------------------------------------------------------------")
        print(f"\tComplete statistics for duration 0.0 - {stop:.1f}")
    print("----------------------------------------------------------------")
    print(f"ID\t\tInterval\t{'Transferred' if role == 'Client' else 'Received'}\tRate")
    print(f"{server_ip}:{port}\t{start:.1f}-{stop:.1f}s\t{transfer_mb:.0f}{unit}\t\t{rate:.2f} {speed}")

def parsedArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--server", help="Runs simpleperf in server mode", action="store_true")
    parser.add_argument("-c", "--client", help="Runs simpleperf in client mode", action="store_true")
    parser.add_argument("-b", "--bind", type=str, help="Used to set IP address of server's interface", default="127.0.0.1")
    parser.add_argument("-p", "--port", type=int, help="Used to set port number for server to listen on", default=8088)
    parser.add_argument("-f", "--format", type=str, choices=["B", "KB", "MB"], help="What format to show the results in", default="MB")
    parser.add_argument("-I", "--server-ip", type=str, help="Sets IP adress of the server", default="127.0.0.1")
    parser.add_argument("-t", "--time", type=int, help="Total duration for data to be generated and sent to server", default=25)
    parser.add_argument("-i", "--interval", type=int, help="Prints statistics per z seconds", default=25)
    parser.add_argument("-P", "--parallel", type=int, choices=range(1, 6), help="Create specified numbers of instances to the server", default=1)
    parser.add_argument("-n", "--num", type=str, help="Transfer number of bytes specified by -n flag")
    
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parsedArgs()

    if args.server:
        serverSide(args.bind, args.port, args.format, args.interval)
    elif args.client:

        local_ip = socket.gethostbyname(socket.gethostname())
        clientThreads = []

        if args.num is not None:
            num = parseNum(args.num)
        else:
            num = None
        for n in range(args.parallel):
            local_port = args.port + n +1
            t = threading.Thread(target=clientSide, args=(local_ip, local_port, args.server_ip, args.port, args.time, args.format, args.interval, num))
            clientThreads.append(t)
            t.start()

        for t in clientThreads:
            t.join()
