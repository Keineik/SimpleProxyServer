import threading
from socket import *

import sys

def handleGET(message):
    path = message.decode().split()[1]

    http_pos = path.find("://")
    if (http_pos != -1):
        path = path.partition("://")[2]
    webServer, file = path.split("/")

    s = socket(AF_INET, SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect((webServer, 80))

        # Create request to web server
        requestLine = f"GET /{file} HTTP/1.1\r\n"
        hostLine = f"Host: {webServer}\r\n"
        msgSend = requestLine + hostLine + "Connection: close\r\n\r\n"
        # Send request to web server
        s.send(msgSend.encode())
        print(f"[*->] Sending request to web server: \n{msgSend}")

        # Receive reply from web server
        msg = b""
        while True:
            chunk = s.recv(1024)
            if len(chunk) <= 0: 
                break
            msg += chunk
        try:
            print(f"[*<-] Received web server response: \n{msg.decode()}")
        except:
            print(f"[*<-] Received web server response: \n{msg.decode('latin1')}")
        
        # Send reply from web server to client
        print(f"[<-*] Sending reply to client \n{msg.decode()}")
        clientSock.send(msg)
        
        s.close()
        clientSock.close()
    except socket.timeout:
        print("Connection timed out. Unable to connect.")
        s.close()
        clientSock.close()

    return

def handleClient(clientSock, addr):
    # Receive message from client
    message = b""
    while True:
        chunk = clientSock.recv(1024)
        if len(chunk) <= 0:
            break   
        message += chunk
        print(f"[->*] Request from user: {addr}")
        print(message.decode())
        
        # Extract the information from the given message
        requestLine = message.decode().split('\r\n')[0]
        method = message.decode().split()[0]
        path = message.decode().split()[1]

        proxy = False
        # Handle the request by type
        if method == "GET":
            handleGET(message)
        elif method == "HEAD":
            clientSock.close()
            return
        elif method == "POST":
            clientSock.close()
            return
        else:
            # Response 403 Forbidden for unsupported methods
            clientSock.close()
            return
    clientSock.close()
    return


if len(sys.argv) <= 1:
    print('Usage : "python ProxyServer.py server_ip"\n[server_ip : It is the IP Address Of Proxy Server')
    sys.exit(2)
# Client test: curl --proxy "127.0.0.1:8888" "http://example.com" -v
# Create a server socket, bind it to a port and start listening
serverSock = socket(AF_INET, SOCK_STREAM)
serverSock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

HOST = sys.argv[1].split(':')[0]
PORT = int(sys.argv[1].split(':')[1])
serverSock.bind((HOST, PORT))

serverSock.listen(5)
while True:
    # Start receiving data from the client
    print('Ready to serve...')
    clientSock, addr = serverSock.accept()
    print('Received a connection from:', addr)
    # Create a new thread and run
    thread = threading.Thread(target=handleClient, args=(clientSock, addr))
    thread.start()