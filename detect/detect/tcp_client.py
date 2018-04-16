#!/usr/bin python
# coding: UTF-8

import time
import sys
import socket
import datetime
import re
import binascii
from get_config import get_global_config,default_resolve_dns,resolve_dns
from log import trace_err
from detect_log import *

DEFAULT_RECV_TIMEOUT = 5


class TcpServer:
    def __init__(self,server_name,ip,request_content,response_content,nameserver,port=None,timeout=None):       
        self.servername = server_name
        self.ip = ip
        self.request_content = request_content
        self.response_content = response_content
        self.nameserver = nameserver
        self.port = port if port is not None else 80
        #self.timeout = timeout if timeout is not None else DEFAULT_RECV_TIMEOUT
        self.timeout = timeout

    def checkip(self,test_ip):
        '''
        正则匹配，判断是否是ip
        '''
        p = re.compile('^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$')
        if p.match(test_ip):
            return True
        else:
            return False

    def SendData(self):
        '''
        tcp探测,获取建联时间
        '''
        BUFFSIZE = 1024
        sockfd = None
        start_time = None
        end_time = None
        take_time = None
        take_time_sec = None
        take_time_mic_sec = None
        take_time_mil_sec = None
        test_ip = None
        msg1 = None

        try:
            sockfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sockfd.settimeout(self.timeout)

            if self.checkip(self.ip) == True:
                test_ip = self.ip
            else:
                if self.nameserver == None:
                    ip_name_dict = default_resolve_dns(self.ip)
                    if len(ip_name_dict) > 0:
                        test_ip = ip_name_dict[self.ip][0]
                        log_data.info("dns of [%s] return line:[%s" % (self.ip,test_ip))
                    else:
                        pass
                else:
                    ip_name_dict = resolve_dns(self.ip)
                    if len(ip_name_dict) > 0:
                        test_ip = ip_name_dict[self.ip][0]
                        log_data.info("dns of [%s] return line:[%s" % (self.ip,test_ip))
                    else:
                        pass
            start_time = datetime.datetime.now()
            if test_ip is not None:            
                fd = sockfd.connect((test_ip,self.port))
            end_time = datetime.datetime.now()
            take_time = end_time - start_time
            take_time_sec = take_time.seconds
            take_time_mic_sec = take_time.microseconds
            take_time_mil_sec = (take_time_sec * 1000) + (take_time_mic_sec/1000)
            msg=binascii.a2b_hex(self.request_content)
            #print "msg=%s" % str(msg)
            sockfd.send('%s\r\n' % msg) 
            while True:
                data = sockfd.recv(BUFFSIZE)
                #print "data=%s" % str(data)
                if not data:
                    break
                msg1 = binascii.b2a_hex(data)
                #print "msg1 = %s" % str(msg1)
            sockfd.close()
        except Exception,e:
            log_message.error("Error in TcpServer: %s" % str(e))
        return (take_time_mil_sec,msg1)



if __name__ == '__main__':
    #t = TcpServer('mydevice','www.baidu.com','GET / HTTP/1.1\r\n','abcdef','8.8.8.8',80,6)
    t = TcpServer('mydevice','127.0.0.1','77656C636F6D0D0A','77656C','8.8.8.8',80,6)
    res = t.SendData()
    print res




