import socket


def application(environ, start_response):
    status = '200 OK'
    s=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect("/usr/local/samm/var/samm.sock")
    output=b''
    while True:
        o = s.recv(1024)
        if len(o) == 0:
            break
        output += o

    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]
