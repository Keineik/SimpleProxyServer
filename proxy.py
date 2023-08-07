import threading
from socket import *

import sys

def handleWebServer(webServer, msgSend):
    s = socket(AF_INET, SOCK_STREAM)
    s.connect((webServer, 80))
    # Send request to web server
    s.send(msgSend)
    print(f"[*->] Sending request to web server: \n{msgSend.decode()}\r\n")

    # Receive reply from web server
    msg = b""
    while True:
        chunk = s.recv(1024)
        if len(chunk) <= 0: 
            break
        msg += chunk
    try:
        print(f"[*<-] Received web server response: \n{msg.decode()}\r\n")
    except:
        print(f"[*<-] Received web server response: \n{msg.decode('latin1')}\r\n")
    
    return msg

def handleGET(message):
    # Get web server and file path from message
    method = message.decode().split()[0]
    path = message.decode().split()[1]
    http_pos = path.find("://")
    if (http_pos != -1):
        path = path.partition("://")[2]
    webServer, trash, file = path.partition("/")
    file = "/" + file

    # Create message to be sent to web server
    requestLine = f"{method} {file} HTTP/1.1\r\n"
    msgSend = requestLine 
    msgSend += message.decode().partition("\r\n")[2].partition("\r\n\r\n")[0]
    msgSend += "\r\nConnection: close\r\n\r\n"

    # Connect to web server and get reply
    msg = handleWebServer(webServer, msgSend.encode())

    # Send reply to client
    print(f"[<-*] Sending reply to client\r\n")
    clientSock.send(msg)

    return

def handlePOST(message):
    # Get web server from message
    method = message.decode().split()[0]
    path = message.decode().split()[1]
    http_pos = path.find("://")
    if (http_pos != -1):
        path = path.partition("://")[2]
    webServer, trash, file = path.partition("/")
    file = "/" + file

    # Create message to be sent to web server
    requestLine = f"{method} {file} HTTP/1.1\r\n"
    msgSend = requestLine 
    msgSend += message.decode().partition("\r\n")[2].partition("Connection: ")[0]
    msgSend += "Connection: close\r\n"
    msgSend += message.decode().partition("Connection: ")[2].partition("\r\n")[2]

    # Connect to web server and get reply
    msg = handleWebServer(webServer, msgSend.encode())

    # Send reply to client
    print(f"[<-*] Sending reply to client\r\n")
    clientSock.send(msg)

    return

def handleClient(clientSock, addr):
    # Receive message from client
    message = b""
    while True:
        chunk = clientSock.recv(1024)
        if len(chunk) <= 0:
            break   
        message += chunk
        print(f"[->*] Request from user: {addr}\r\n")
        try:
            print(f"{message.decode()}\r\n")
        except:
            clientSock.close()
            return
        
        # Extract the information from the given message
        requestLine = message.decode().split('\r\n')[0]
        method = message.decode().split()[0]
        path = message.decode().split()[1]

        # Handle the request by type
        if method == "GET":
            handleGET(message)
            clientSock.close()
            return
        elif method == "HEAD":
            clientSock.close()
            return
        elif method == "POST":
            handlePOST(message)
            clientSock.close()
            return
        else:
            # Response 403 Forbidden for unsupported methods
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
    #thread = threading.Thread(target=handleClient, args=(clientSock, addr))
    #thread.start()
    handleClient(clientSock, addr)