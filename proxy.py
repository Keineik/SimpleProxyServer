import threading
from socket import *
import json
from datetime import datetime
import sys

def getconfig():
    fileConfig = open('config.json')
    configs = json.load(fileConfig) 
    return configs['cache_time'], configs['whitelisting_enabled'], configs['whitelist'], configs['time_restriction'], configs['time_range']
cache_time, whitelisting_enabled, whitelist, time_restriction, time_range = getconfig()

def isInTimeRange():
    if time_restriction == 0:
        return True
    now = datetime.now().strftime("%H")
    start, trash, end = time_range.partition('-')
    return int(start) <= int(now) <= int(end)
    

def handleForbiddenAction():
    with open("error403.html", 'r') as file:
        data = file.read()
    reply = f"HTTP/1.1 403 Forbidden\r\n\r\n{data}"
    return reply.encode()

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
    if (path.find("://") != -1):
        path = path.partition("://")[2]
    webServer, trash, file = path.partition("/")
    file = "/" + file
    return method, webServer, file

def handleHEAD_GET_POST(message):
    # Get method, web server and file path from message
    method, webServer, file = getInfoFromMessage(message)

    # Create request to be sent to web server
    request = f"{method} {file} HTTP/1.1\r\n"
    if method == "POST":
        if message.decode().find("Connection: ") != -1:
            request += message.decode().partition("\r\n")[2].partition("Connection: ")[0]
            request += "Connection: close\r\n"
            request += message.decode().partition("Connection: ")[2].partition("\r\n")[2]
        else:
            temp = message.decode().partition("\r\n\r\n")
            request += temp[0]
            request += "\r\nConnection: close\r\n\r\n"
            request += temp[2]
    else:
        request += f"Host: {webServer}\r\n\r\n"
        request += f"Connection: close\r\n\r\n"

    # Connect to web server and get reply
    webServerSock = socket(AF_INET, SOCK_STREAM)
    webServerSock.connect((webServer, 80))
    webServerSock.send(request.encode())
    # Receive reply from web server
    fragments = []
    while True:
        chunk = webServerSock.recv(1024)
        if not chunk:
            break
        fragments.append(chunk)
    data = b"".join(fragments)

    webServerSock.close()
    return data

def handleClient(clientSock, addr):
    # Receive message from client
    message = clientSock.recv(4096)
    if not message:
        return
    try:
        print(f"[->*] Request from user: {addr}\n{message.decode()}\r\n")
    except:
        clientSock.close()
        return
    
    # Extract the method from the given message
    method, webServer, file = getInfoFromMessage(message)

    # Check whitelisting and time restriction
    if isInTimeRange() == False:
        reply = handleForbiddenAction()
    elif whitelisting_enabled == 1 and webServer in whitelist:
        reply = handleForbiddenAction()
    # Handle the request by type
    elif method in ["HEAD", "GET", "POST"]:
        reply = handleHEAD_GET_POST(message)
    else:
        reply = handleForbiddenAction()
    
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

serverSock.listen(10)
print("Ready to serve: ")
while True:
    # Start receiving data from the client
    clientSock, addr = serverSock.accept()
    # Create a new thread and run
    thread = threading.Thread(target=handleClient, args=(clientSock, addr))
    #thread.setDaemon(1)
    thread.start()