#!usr/bin python
# -*- coding:utf-8 -*-

import httplib
import os
import time
import sys
import datetime
import re
import threading
from detect_log import *
from get_config import get_global_config,default_resolve_dns,resolve_dns
from log import trace_err

class HttpSendData:
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
        p = re.compile('^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$')
        if p.match(test_ip):
            return True
        else:
            return False        
        
    def send_data(self):

        httpClient = None

        start_time = None
        end_time = None
        take_time = None
        take_time_sec = None
        take_time_mic_sec = None
        take_time_mil_sec = None 
        test_ip = None
        content = None
        try:
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
                httpClient = httplib.HTTPConnection(test_ip,self.port,self.timeout)
            if httpClient is not None:
                httpClient.request('GET',self.request_content)
                response = httpClient.getresponse()
                end_time = datetime.datetime.now()
                take_time = end_time - start_time
                take_time_sec = take_time.seconds 
                take_time_mic_sec = take_time.microseconds
                take_time_mil_sec = (take_time_sec * 1000) + (take_time_mic_sec/1000)
                print take_time_mil_sec
                http_status = response.status
                print http_status
                log_data.info("http of [%s] return line:[%s" % (self.ip,take_time_mil_sec))
                if http_status == 200:
                    content = response.read()
                else:
                    content = 'error'
        except Exception,e: 
           trace_err()
           log_message.error("Error detect http send_data func : %s" % str(e))
        else:
            log_data.info("http of [%s] return line:[%s" % (self.ip,take_time_mil_sec))
        finally:
            if httpClient:
                httpClient.close()

        return (take_time_mil_sec,content)

def dns_detect():
    t = HttpSendData('mydevice','www.12306.com','/','abcdef','8,8.8.8',80,6)
    res = t.send_data()
    print res

if __name__ == '__main__':
    t_dns = threading.Thread(target=dns_detect,args=[])
    t_dns.setDaemon(True)
    t_dns.start()
    time.sleep(60)




