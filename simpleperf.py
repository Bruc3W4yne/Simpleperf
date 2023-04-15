import socket
import sys
import argparse
import time
import sched

def serverSide(bindAdress, port, format, interval=None, buffer_size=1000):
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

        while True:
            data = clientSocket.recv(buffer_size)
            bytes_received += len(data)

            if b"BYE" in data:
                duration = time.time() - start_time
                transfer_mb = bytes_received / (1024 * 1024)

                clientSocket.sendall(b"ACK : BYE")
                formattedResults("Server", clientAddress[0], clientAddress[1], transfer_mb, duration, format)
                break

        clientSocket.close()


def clientSide(server_ip, port, duration, format, buffer_size=1000):
    print(f"A simpleperf client connecting to server <{server_ip}>, port {port}")

    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket.connect((server_ip, port))

    print(f"Client connected with {server_ip}, port {port}")

    start_time = time.time()
    bytes_sent = 0
    data = bytes(buffer_size)

    while time.time() - start_time < duration:
        clientSocket.sendall(data)
        bytes_sent += buffer_size

    clientSocket.sendall(b"BYE")
    ack = clientSocket.recv(buffer_size)

    if b"ACK : BYE" in ack:
        duration = time.time() - start_time
        transfer_mb = bytes_sent / (1024 * 1024)
        formattedResults("Client", server_ip, port, transfer_mb, duration, format)
        
    clientSocket.close()

def formattedResults(role, server_ip, port, transfer_mb, duration, format):
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

    rate = (transfer_mb * 8) / duration
    print(f"ID\tInterval\t{'Transferred' if role == 'Client' else 'Received'}\tRate")
    print(f"{server_ip}:{port}\t0.0-{duration:.1f}s\t{transfer_mb:.0f}{unit}\t{rate:.2f} {speed}")

def parsedArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--server", help="Runs simpleperf in server mode", action="store_true")
    parser.add_argument("-c", "--client", help="Runs simpleperf in client mode", action="store_true")
    parser.add_argument("-b", "--bind", type=str, help="Used to set IP address of server's interface", default="127.0.0.1")
    parser.add_argument("-p", "--port", type=int, help="Used to set port number for server to listen on", default=8088)
    parser.add_argument("-f", "--format", type=str, choices=["B", "KB", "MB"], help="What format to show the results in", default="MB")
    parser.add_argument("-I", "--server-ip", type=str, help="Sets IP adress of the server", default="127.0.0.1")
    parser.add_argument("-t", "--time", type=int, help="Total duration for data to be generated and sent to server", default=25)
    parser.add_argument("-i", "--interval", type=int, help="Prints statistics per z seconds", default="25")
    parser.add_argument("-P", "--parallel", type=int, choices=range(1, 6), help="Create specified numbers of instances to the server", default=1)
    parser.add_argument("-n", "--num", type=str, help="Transfer number of bytes specified by -n flag")
    
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parsedArgs()

    if args.server:
        serverSide(args.bind, args.port, args.format, args.interval)
    elif args.client:
        clientSide(args.server_ip, args.port, args.time, args.format)
