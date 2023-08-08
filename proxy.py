import threading
from socket import *

import sys

def replyClient(clientSock, reply):
    # Send reply to client
    clientSock.send(reply)

    # Process what to print
    try:
        header = reply.decode().partition("\r\n\r\n")[0]
    except:
        header = reply.decode('latin1').partition("\r\n\r\n")[0]
    if header.find("Content-Type: ") != -1 and header.find("text") != -1:
        try:
            print(f"[<-*] Send reply to client: \n{reply.decode()}")
        except:
            print(f"[<-*] Send reply to client: \n{header}\r\n\r\nNOT TEXT, CAN'T SHOW OR FAILED TO DECODE")
    else:
        print(f"[<-*] Send reply to client: \n{header}\r\n\r\nNOT TEXT, CAN'T SHOW")

    return

def getInfoFromMessage(message):
    # Get method, web server and file path from message
    method = message.decode().split()[0]
    path = message.decode().split()[1]
    http_pos = path.find("://")
    if (http_pos != -1):
        path = path.partition("://")[2]
    webServer, trash, file = path.partition("/")
    file = "/" + file
    return method, webServer, file

def handleHEAD(message):
    # Get method, web server and file path from message
    method, webServer, file = getInfoFromMessage(message)

    # Create HEAD message to be sent to web server
    headerRequest = f"HEAD {file} HTTP/1.1\r\n"
    headerRequest += f"Host: {webServer}\r\n\r\n"
    headerRequest += f"Connection: close\r\n\r\n"

    # Connect to web server and get reply
    headSocket = socket(AF_INET, SOCK_STREAM)
    headSocket.connect((webServer, 80))
    headSocket.send(headerRequest.encode())
    # Receive reply from web server
    httpHeader = headSocket.recv(4096)

    headSocket.close()
    return httpHeader

def handleGET(message):
    # Get method, web server and file path from message
    method, webServer, file = getInfoFromMessage(message)

    # Create GET message to be sent to web server
    getRequest = f"{method} {file} HTTP/1.1\r\n"
    getRequest += f"Host: {webServer}\r\n"
    getRequest += f"Connection: close\r\n\r\n"

    # Connect to web server and get reply
    getSocket = socket(AF_INET, SOCK_STREAM)
    getSocket.connect((webServer, 80))
    getSocket.send(getRequest.encode())
    # Receive reply from web server
    fragments = []
    while True:
        chunk = getSocket.recv(1024)
        if not chunk:
            break
        fragments.append(chunk)
    data = b"".join(fragments)

    getSocket.close()
    return data

def handlePOST(message):
    # Get method, web server and file path from message
    method, webServer, file = getInfoFromMessage(message)

    # Create POST message to be sent to web server
    postRequest = f"{method} {file} HTTP/1.1\r\n"
    if message.decode().find("Connection: ") != -1:
        postRequest += message.decode().partition("\r\n")[2].partition("Connection: ")[0]
        postRequest += "Connection: close\r\n"
        postRequest += message.decode().partition("Connection: ")[2].partition("\r\n")[2]
    else:
        temp = message.decode().partition("\r\n\r\n")
        postRequest += temp[0]
        postRequest += "\r\nConnection: close\r\n\r\n"
        postRequest += temp[2]

    # Connect to web server and get reply
    postSocket = socket(AF_INET, SOCK_STREAM)
    postSocket.connect((webServer, 80))
    postSocket.send(postRequest.encode())
    # Receive reply from web server
    fragments = []
    while True:
        chunk = postSocket.recv(1024)
        if not chunk:
            break
        fragments.append(chunk)
    data = b"".join(fragments)

    postSocket.close()
    return data

def handleClient(clientSock, addr):
    # Receive message from client
    message = b""
    while True:
        message = clientSock.recv(4096)
        if not message:
            return
        try:
            print(f"[->*] Request from user: {addr}\n{message.decode()}\r\n")
        except:
            clientSock.close()
            return
        
        # Extract the method from the given message
        method = message.decode().split()[0]

        # Handle the request by type
        if method == "GET":
            reply = handleGET(message)
        elif method == "HEAD":
            reply = handleHEAD(message)
        elif method == "POST":
            reply = handlePOST(message)
        else:
            # Response 403 Forbidden for unsupported methods
            clientSock.close()
            return
        
        # Reply to client
        replyClient(clientSock, reply)

        clientSock.close()
        return
    

if len(sys.argv) != 2:
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
print("Ready to serve: ")
while True:
    # Start receiving data from the client
    clientSock, addr = serverSock.accept()
    # Create a new thread and run
    thread = threading.Thread(target=handleClient, args=(clientSock, addr))
    thread.setDaemon(1)
    thread.start()