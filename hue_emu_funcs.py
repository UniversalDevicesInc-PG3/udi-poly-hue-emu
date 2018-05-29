

import socket

# from http://commandline.org.uk/python/how-to-find-out-ip-address-in-python/
def get_network_ip(rhost):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((rhost, 0))
    ip = s.getsockname()[0]
    s.close()
    return ip
