def checkifWhitelist(webServer, whitelists):
    allowed = False
    for whitelist in whitelists:
        if whitelist == webServer:
            allowed = True
    return allowed
def handleForbiddenAction(clientSock):
    fileerr = open("error403.html", "r")
    rawhtml = fileerr.readlines()
    requestline = f"HTTP/1.1 403 Forbidden\r\n"
    htmlcode = ""
    for line in rawhtml:
        htmlcode += line
    response = requestline + "\r\n" + htmlcode
    clientSock.sendall(response.encode())
    clientSock.close()