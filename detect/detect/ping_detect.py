#!/usr/bin python
# -*- coding: utf-8 -*-


import sys
import os
import time
import subprocess


from get_config import get_all_config
from detect_log import *

bad_value = 99999
def get_time_value(test_result_values):
    
    if not test_result_values:
        log_message.error("error, want to get time value from NULL line ")
        return bad_value

    return_value = bad_value
    line = test_result_values
    time_index = line.find("time=")
    if(time_index != -1):
        end = line[time_index + 5:].find(" ")
        if(end != -1):
            time = line[time_index + 5 : time_index + 5 + end]
            return_value = float(time)
    return return_value

def sys_ping(server_name,dst_ip,ping_interval,pkt_size,timeout):

    #global ping_test
    global test_result
    start_time = None
    cstdout = None
    test_value = None
    cmd = None
    first = 0
    try:
        cmd = "/bin/ping -i" + str(ping_interval) +  " -W " + str(timeout) + " -s " + str(pkt_size) + " " + str(dst_ip)
    except Exception,e:
        log_message.error("ping detect exit ...get ping cmd for ip:[%s ][%s] error: %s" % (dst_ip, server_name, str(e)))
        return
    log_message.info(str(cmd))
    try:
        sub_p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        cstdout = sub_p.stdout
    except Exception,e:
        log_message.error("ping detect exit ...start %s error: %s" % (str(cmd),str(e)))
        return
    while True:
        try:
            p_result = cstdout.readline()
            if first:
                if p_result:
                    log_data.info(str(p_result))
                    first = 0
                    continue
            if p_result:
                log_data.info("ping of [%s] return line:\n[%s" % (dst_ip,p_result))
                test_value = get_time_value(p_result)
            
                log_data.info("ping of [%s] return line:\n\n[%s" % (dst_ip,test_value))
                if(test_value == bad_value):
                    continue
                ping_test = test_value
            else:
                log_message.error("%s: has recv None, test process exit now ..." % str(cmd))
        except Exception,e:
            print "exception....%s" %(str(e))

            log_message.critical("ping server exit ...error in %s: %s..." % (str(cmd), str(e)))

            return

if __name__=='__main__':

   ip = sys_ping('weee','www.qq.com',10,56,10)
   print ip







      







