#!/usr/bin python 
# -*- coding: utf-8 -*-


import socket

from SocketServer import (TCPServer as TCP, StreamRequestHandler as SRH)  
from time import ctime 

HOST = '127.0.0.1'
PORT = 80

ADDR = (HOST, PORT)  

def TcpServe():

    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.bind( ADDR)
    s.listen(5)
    while 1:
        sock,addr=s.accept()
        print "got connection form ",sock.getpeername()
        data=sock.recv(1024)
        if not data:
            break
        else:
            print data

class MyRequestHandler(SRH):  
    def handle(self):  
        print '...connect from:', self.client_address  
        self.wfile.write('[%s] %s' % (ctime(), self.rfile.readline()))  


if __name__ == '__main__':
    tcpServ = TCP(ADDR, MyRequestHandler)  
    print 'waiting for connection...'  
    tcpServ.serve_forever()
