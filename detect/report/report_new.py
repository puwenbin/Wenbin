#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
实现探测数据上报
"""

import time
import Queue
import threading
from report_log import*
from SimpleXMLRPCServer import SimpleXMLRPCServer
import os
import datetime
import subprocess
import traceback
import sys
import re
import datetime
from commands import getoutput
from datasave import DataSaveThread
sys.path.append("..")
from detect.get_config import get_global_config,get_customer_name
customer_list = get_customer_name()
global_config_dict = get_global_config()
report_addr = global_config_dict["report_addr"]
report_port = global_config_dict["report_port"]
PID_FILE = "/root/report.pid "
all_customer_queue_data = {}

#print "detect_data = %s" % detect_data
mutex = threading.Lock()

def trace_err(ext_msg=None):
    '''
    捕或异常
    '''
    msg = '' if ext_msg is None else ext_msg
    msg += '\n------------------- Local Args -------------------\n'
    for k, v in sys._getframe(1).f_locals.iteritems():
        msg += (' >>> ' + str(k) + ': ' + str(v) + '\n')
    msg += '--------------------- Error ----------------------\n'
    exc_info = traceback.format_exception(*sys.exc_info())
    msg += ''.join(exc_info)
    msg += '---------------------- End -----------------------\n'
    log_message.error(msg)

   
class ReportThread(threading.Thread):
    '''
    创建listening事件，创建队列reports保存上报数据
    '''
    def __init__(self,reports,listening,host_ip,host_port):

        super(ReportThread, self).__init__()
        self.reports = reports
        self.listening = listening
        self.host_ip = host_ip
        self.host_port = host_port
        self.sys_health = True
        self.setName('ReportThread')
    
    def get_self_report(self):
        return self.reports

    def p_running1(self,p_name):
        ''' 
        program p_name is runing ? 
        if running, return pid; else return 0
        '''
        ret = 0
        f = None
        s_f = None
        if(not os.path.isfile(PID_FILE)):
            return 0
        try:
            f = open(PID_FILE, 'r')
            pid = int(f.read(len(p_name)))
            if(pid > 0):
                status_file = str("/proc/%d/status" % pid)
                if(not os.path.isfile(status_file)):
                    return 0
                s_f = open(status_file, 'r')
                line = s_f.readline()
                log_message.info(str("/proc/%d/status: %s" % (pid, line)))

                if(line.find(p_name)):
                    log_message.info(str("%s is already running ..." % p_name))
                    ret = pid
                else:
                    ret = 0
                s_f.close()
            else:
                ret = 0
        except IOError, e:
            log_message.error(str(e))

            if(f):
                f.close()
            if(s_f):
                s_f.close()
            return 0
        f.close()
        return ret
    
    def sys_command(self,command,record = True):
        '''
        执行系统命令
        '''
        if record == True:
            log_message.info("输出命令:%s" % command)
        return getoutput(command)

    def p_running(self,p_name):
        '''
        检测程序是否在运行
        '''
        try:
            cmd = "ps -ef | grep -e %s | grep -v grep |  awk '{print $2}'" % p_name
            pids = self.sys_command(cmd)
            log_message.info("%s 程序进程ID：%s"%(p_name, pids))
            return [] if not pids else pids.split('\n')
        except Exception,e:
            log_message.error("error in p_running:%s" % str(e))
            trace_err()

    def run_multi_rpc_server(self,host_ip, host_port, listen_func_list):
        '''
        启动rpc服务,注册函数
        '''
        srv = SimpleXMLRPCServer((host_ip, host_port), allow_none=True)
        for func in listen_func_list:
            srv.register_function(func)
        srv.serve_forever()
        
    def report_to_ldc(self,report_data):
        '''
        接收设备探测数据(供探测端调用的XML_RPC端口)
        report_data:上报的数据,列表类型
        '''
        try:
            if not self.listening.is_set():
                self.reports.put(report_data)
                log_message.info("收到探测端上报的数据:%s" %  str(report_data))
                return True
            else:
                log_message.info("上报延迟: %s" % str(report_data))
                return False
        except Exception,e:
            log_message.error("error in report_to_ldc:%s ..." % str(e))
            trace_err()
            return False
    
	
    def echo_ldc(self):
        try:
            if self.sys_health:
                return 'busy' if self.listening.is_set() else 'listening'
            else:
                return 'fault'
        except Exception,e:
            log_message.error("error in echo_ldc:%s ..." % str(e))
            trace_err()

    def get_ldc_start_up_time(self):
        '''
        获取LDC端系统启动时间
        '''
        start_time = None
        ldc_start_time = None
        pid = self.p_running("report")
        #print pid
        if pid[0] > 0:
            #print pid[0]
            start_time = time.time()
            ldc_start_time = int(start_time)
            print ldc_start_time
        return ldc_start_time

    def run(self):
        '''
        启动上报线程
        '''
        try:
            log_message.info("启动上报线程")
            #print "启动上报线程"
            func_list = (self.report_to_ldc,self.echo_ldc,self.get_ldc_start_up_time)
            self.run_multi_rpc_server(self.host_ip,self.host_port,func_list)
        except Exception,e:
            log_message.error("error in ReportThread: %s" % str(e))
            trace_err()

class DataHandleThread(threading.Thread):
    '''
    从队列中取出数据
    '''
    def __init__(self,reports):
        super(DataHandleThread, self).__init__()
        self.reports = reports
        self.setName('DataHandletThread')

    def pop_queue(self):
        '''
        从队列中取出数据
        '''
        try:
            for i in xrange(self.reports.qsize()):
                return self.reports.get()
                #return [self.reports.get() for i in xrange(self.reports.qsize())]
        except Exception,e:
            log_message.error("error in pop_queue:%s" % str(e))
            trace_err()

    def get_lock(self):
        try:
            mutex.acquire()
            log_message.info("get the lock ...")
            return True
        except Exception,e:
            log_message.error("get the lock failed:%s ..." % str(e))
            return False
    def release_lock(self):
        try:
            mutex.release()
            log_message.info("release the lock...")
            return True
        except Exception,e:
            log_message.error("release the lock failed:%s ..." % str(e))
            return False


    def run(self):

        while True:
            while self.reports.qsize() == 0:
                pass
            log_message.info("启动数据处理线程")
            #print "queue_size = %d" % self.reports.qsize()
            detect_data = []
            get_queue_data = self.pop_queue()
            #print "get_queue_data = %s" % str(get_queue_data)
            detect_value = get_queue_data[0]
            detect_offsent = get_queue_data[1]['offsent']
            src_device = get_queue_data[2]['src_device']
            customer_keys = detect_value.keys()
            print customer_keys
            global all_customer_queue_data
            customer_que_dict = {}
            for customer_key in customer_keys:
                customer_queue_data = []
                dst_device_keys =detect_value[customer_key].keys()
                for dst_device_key in dst_device_keys:
                    detect_templates = detect_value[customer_key][dst_device_key].keys()
                    for detect_template in detect_templates:
                        detect_value_list = detect_value[customer_key][dst_device_key][detect_template]['detect_time']
                        detect_time_list = detect_value[customer_key][dst_device_key][detect_template]['detect_timestamp']
                        data_timestamp = int(detect_time_list[0]) - int(detect_offsent)
                        timestamp = time.localtime(data_timestamp)
                        first_data_timestamp = time.strftime("%Y-%m-%d %H:%M:%S",timestamp)  
                        queue_data_temp = [str(src_device),str(dst_device_key),str(detect_template),str(detect_value_list),str(detect_time_list),str(first_data_timestamp),str(detect_offsent)]
                        customer_queue_data.append(queue_data_temp)
                customer_que_dict = {customer_key:customer_queue_data}
                self.get_lock()
                all_customer_queue_data.update(customer_que_dict)
                self.release_lock()
            
def main():
    try:
        pid = os.getpid()
        p_f = open(PID_FILE,'w')
        p_f.write(str(pid))
        p_f.close()
    except Exception,e:
        log_message.error(str(e))
        os._oxit(1)
    listening = threading.Event()
    reports = Queue.Queue()
    print "start ReportThread"
    listener = ReportThread(reports,listening,report_addr,int(report_port))
    listener.setDaemon(True)
    listener.start()
    #time.sleep(20)
    print "start DataHandleThread"
    datahandle = DataHandleThread(reports)
    datahandle.setDaemon(True)
    datahandle.start()
    host = report_addr
    user_name = 'root'
    passwd = ''
    charset="utf8"
    db_name = "device_detect_database"

    #global detect_data 
    #print "--------------"
    #params = (('23','http','5678','890','32','21'),('23','45','http','890','5678','45'),('23','ping','56','56','78','34'),('54','ping','34','54','12','12'))
    #params_list = [[['23','http','5678','890','32','21'],['23','45','http','890','5678','45']],[['23','ping','56','56','78','34'],['54','ping','34','54','12','12']    ]]
    while True:
        if len(all_customer_queue_data) > 0:
            for customer_key in all_customer_queue_data.keys():
                table_name = customer_key
                #print table_name
                print all_customer_queue_data.keys()
                params = all_customer_queue_data[customer_key]
                data = DataSaveThread(host,user_name,passwd,db_name,charset,params,table_name)
                data.setDaemon(True)
                data.start()
                data.join()
            all_customer_queue_data.clear() 
    #datahandle.join()
    #listener.join()

def hello(conn):
    return conn

def echo_ldc():
    return "listening"
  
def report_to_ldc(report_data):
    return True



def start_up_rpc():
    try:
        host_ip = "127.0.0.1"
        host_port = 80
        #svr = SimpleXMLRPCServer((host_ip, host_port), allow_none=True)
        svr = SimpleXMLRPCServer(("127.0.0.1",80),allow_none=True)
        svr.register_function(hello)
        svr.register_function(echo_ldc)
        svr.register_function(report_to_ldc)
        svr.serve_forever()
    except Exception,e:
        log_message.error("error in start_up_rpc:%s" % str(e))



if __name__ == '__main__':
    
    #start_up_rpc()
    main()
    #pass
    while True:
        time.sleep(600)














