import threading
from socket import *
import json
import datetime
from time import strptime
import sys
import os

def getconfig():
    fileConfig = open('config.json')
    configs = json.load(fileConfig) 
    return configs['cache_time'], configs['whitelisting_enabled'], configs['whitelist'], configs['time_restriction'], configs['time_range'], configs['decode_format'], configs['supported_img_types']
cache_time, whitelisting_enabled, whitelist, time_restriction, time_range, decode_format, supported_img_types = getconfig()

def isInTimeRange():
    if time_restriction == 0:
        return True
    now = datetime.datetime.now().strftime("%H")
    start, trash, end = time_range.partition('-')
    return int(start) <= int(now) < int(end)

def handleForbiddenAction():
    with open("error403.html", 'r') as file:
        data = file.read()
    reply = f"HTTP/1.1 403 Forbidden\r\n\r\n{data}"
    return reply.encode()

def getInfoFromMessage(message):
    # Get method, web server and file path from message
    method = message.decode(decode_format).split()[0]
    path = message.decode(decode_format).split()[1]
    if (path.find("://") != -1):
        path = path.partition("://")[2]
    webServer, trash, file = path.partition("/")
    file = "/" + file
    return method, webServer, file

def getCachedImage(message):
    method, webServer, file = getInfoFromMessage(message)

    # If does not request image or image type not supported
    filenameExtension = file.split("/").pop().partition(".")[2]
    if filenameExtension not in supported_img_types:
        return False, ""

    # Get the image and image header path
    imgPath = f"{os.getcwd()}/cache/{webServer}{file}"
    imgHeaderPath = imgPath[:imgPath.rfind(".")] + ".bin"

    # If the image is cached
    try:
        with open(imgPath, "rb") as fb:
            img = fb.read()
        with open(imgHeaderPath, "rb") as fb:
            imgHeader = fb.read()
    except:
        return False, ""

    # Get current time and compare with img time + cache time
    currentUTCtime = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    imgTimeStr = imgHeader.decode(decode_format).partition("Date: ")[2].partition(" GMT")[0].partition(", ")[2]
    imgTime = datetime.datetime.strptime(imgTimeStr, "%d %b %Y %H:%M:%S")

    if (imgTime + datetime.timedelta(seconds = int(cache_time)) <= currentUTCtime):
        return False, ""
    return True, imgHeader + b"\r\n\r\n" + img


def saveImageToCache(message, webReply):
    method, webServer, file = getInfoFromMessage(message)

    # If does not request image or image type not supported
    filenameExtension = file.split("/").pop().partition(".")[2]
    if filenameExtension not in supported_img_types:
        return
    
    # Get the path of the image, header and the folder containing them
    imgPath = f"{os.getcwd()}/cache/{webServer}{file}"
    imgHeaderPath = imgPath[:imgPath.rfind(".")] + ".bin"
    folderPath = imgPath[:imgPath.rfind("/")]

    # If the folder does not exist, create that folder
    if not os.path.exists(folderPath):
        try:
            os.makedirs(folderPath)
        except:
            pass

    # Save image and header to cache
    imgHeader, trash, img = webReply.decode(decode_format).partition("\r\n\r\n")
    with open(imgPath, "wb") as fb:
        fb.write(img.encode(decode_format))
    with open(imgHeaderPath, "wb") as fb:
        fb.write(imgHeader.encode(decode_format))
    
    print("SUCCESSFULLY SAVED IMAGE TO CACHE")
    return

def handleHEAD_GET_POST(message):
    # If is cached
    status, cachedReply = getCachedImage(message)
    if status == True:
        print("\r\nGET FROM CACHE SUCCESSFULLY\r\n")
        return cachedReply

    # Get method, web server and file path from message
    method, webServer, file = getInfoFromMessage(message)

    # Create request to be sent to web server
    if message.partition(b"\r\n\r\n")[0].find(b"Connection: ") != -1:
        request = message.partition(b"Connection: ")[0]
        request += b"Connection: close\r\n"
        request += message.partition(b"Connection: ")[2].partition(b"\r\n")[2]
    else:
        request = message.partition(b"\r\n\r\n")[0]
        request += b"Connection: close\r\n"
        request += message.partition(b"\r\n\r\n")[2]

    # Connect to web server and get reply
    webServerSock = socket(AF_INET, SOCK_STREAM)
    webServerSock.connect((webServer, 80))
    webServerSock.send(request)
    # Receive reply from web server
    fragments = []
    while True:
        chunk = webServerSock.recv(1024)
        if not chunk:
            break
        fragments.append(chunk)
    data = b"".join(fragments)

    # Handle Transfer-Encoding: chunked
    dataHeader = data.partition(b"\r\n\r\n")[0]
    if (dataHeader.find(b"chunked") != -1):
        contentLength = "0"
        newData = b""
        noHeader = data.partition(b"\r\n\r\n")[2]

        while True:
            chunkSize = int(noHeader.partition(b"\r\n")[0], base=16)
            if chunkSize == 0:
                break
            contentLength = str(int(contentLength) + chunkSize)

            noHeader = noHeader.partition(b"\r\n")[2]
            newData += noHeader[:chunkSize]
            noHeader = noHeader[chunkSize:].partition(b"\r\n")[2]

        newHeader = data.partition(b"\r\n\r\n")[0]
        # If Transfer-Encoding only contains chunked
        newHeader = newHeader.replace(b"Transfer-Encoding: chunked", b"Content-Length: " + contentLength.encode())
        # If Transfer-Encoding contains other value such as gzip, deflate
        if (newHeader.find(b"chunked") != -1):
            newHeader = newHeader.replace(b", chunked", b"")
            newHeader = newHeader.replace(b" chunked,", b"")
            newHeader += b"Content-Length: " + contentLength.encode(decode_format)
        data = newHeader + b"\r\n\r\n" + newData
    
    # Check if is image and if it is, save to cache
    saveImageToCache(message, data)

    webServerSock.close()
    return data

def handleClient(clientSock, addr):
    # Receive message from client
    message = clientSock.recv(4096)
    if not message:
        clientSock.close()
        return
    # try:
    #     print(f"[->*] Request from user: {addr}\n{message.decode(decode_format)}\r\n")
    # except:
    #     clientSock.close()
    #     return
    
    # Extract the method from the given message
    method, webServer, file = getInfoFromMessage(message)

    # Check whitelisting and time restriction
    if isInTimeRange() == False:
        reply = handleForbiddenAction()
    elif whitelisting_enabled == 1 and webServer not in whitelist:
        reply = handleForbiddenAction()
    # Handle the request by type
    elif method in ["HEAD", "GET", "POST"]:
        reply = handleHEAD_GET_POST(message)
    else:
        reply = handleForbiddenAction()
    
    # Reply to client
    clientSock.sendall(reply)
    clientSock.close()
    return
    
def main():
    if len(sys.argv) != 2:
        print('Usage : "python proxy.py server_ip"\n[server_ip : It is the IP Address Of Proxy Server')
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
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    main()