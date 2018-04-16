#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import sys
import threading
import re
import datetime
import subprocess
import traceback
import platform
import getopt
from log import loginf, trace_code, dbg
from commands import getoutput
from get_config import get_all_config,get_template,get_customer_name,get_global_config,judgment__safety
from detect_log import *
from timeoutproxy import TimeoutServerProxy
import socket
import resource
from xmlrpclib import ServerProxy
from SimpleXMLRPCServer import SimpleXMLRPCServer

from http_client import HttpSendData
from tcp_client import TcpServer


global detect_information_dict
global report_config_dict

bad_value = 2000
count_ping_num = 0


PID_FILE = "/root/detect.pid"
VERSION='0.1.0'
legal = judgment__safety()
#print legal
agent_ldc_offsent_dict = {}
agent_ldc_offsent = None
test_result = {}
report_result = []
main_thread_info = {}
src_name_dict = {}

all_config_dict = get_all_config()

all_template_dict = get_template()
report_config_dict = get_global_config()

report_addr = report_config_dict["report_addr"]
report_port = report_config_dict["report_port"]

DCS = "http://%s:%s" % (report_addr,report_port)

DEBUG = 0     # -d option
QUIET = 0     # -q option

if (hasattr(os, "devnull")):
    NULL_DEVICE = os.devnull
else:
    NULL_DEVICE = "/dev/null"


def trace_err(ext_msg=None):
    '''
    将捕获到的异常信息输出到错误日志(*最好每个 except 后面都加上此函数*)

    直接放到 expect 下即可，E.G.：
        try:
            raise
        except Exception, e:
         :   output_err()

    @params ext_msg: 补充的异常信息
    '''
    msg = u'' if ext_msg is None else ext_msg
    msg += u'\n------------------- Local Args -------------------\n'
    for k, v in sys._getframe(1).f_locals.iteritems():
        msg += (u' >>> ' + unicode(k) + u': ' + unicode(v) + u'\n')
    msg += u'--------------------- Error ----------------------\n'
    exc_info = traceback.format_exception(*sys.exc_info())  # 取出格式化的异常信息
    msg = u"%s %s"%(msg, ''.join(exc_info))
    msg += u'---------------------- End -----------------------\n'
    log_message.error(msg)

def _redirectFileDescriptors():
    '''
    将标准输入和标准输出重定向
    '''
    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if maxfd == resource.RLIM_INFINITY:
        maxfd = 1024
    for fd in range(0,maxfd):
        try:
            os.ttyname(fd)
        except:
            continue
        try:
            os.close(fd)
        except OSError:
            pass
    os.open(NULL_DEVICE, os.O_RDWR)
    os.dup2(0,1)
    os.dup2(0,2)

def python_daemon():
    '''
    将本进程设置为后台启动
    '''
    if os.name != 'posix':
        log_message.info('Daemon is only supported on Posix-compliant systems.')
        return
    try:
        if(os.fork() > 0):
            os._exit(0)
    except OSError:
        log_message.error("创建进程失败")
        os._exit(1)

    os.chdir('/')
    os.setsid()
    os.umask(0)
    try:
        if(os.fork() > 0):
            os._exit(0)
        _redirectFileDescriptors()
    except OSError:
        log_message.error("创建进程失败")
        os._exit(1)



def get_lock():
    try:
        mutex.acquire()
        log_message.info("get the lock ...")
        return True
    except Exception,e:
        log_message.error("get the lock failed:%s ..." % str(e))
        return False

def release_lock():
    try:
        mutex.release()
        log_message.info("release the lock ...")
        return True
    except Exception,e:
        log_message.error("get the lock faild: %s ..." % str(e))
        return False

def sys_command(command, record=True):

    if record:
        dbg(command)
    return getoutput(command)


def p_running(p_name):

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


def get_time_value(test_result_values):
    
    '''
    Get the time value of the ping，if not test_result_values,return bad_value
    '''
    
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

def sys_ping(customer_name,dst_device,template_name,server_name,dst_ip,ping_interval,pkt_size,timeout):

    '''
    实现ping探测：ping_interval,timeout,pkt_size,dst_ip
    '''
    
    global test_result
    start_time = None
    cstdout = None
    test_value = None
    cmd = None
    first = 1
    count_num = 0
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
    #test_result[customer_name][dst_device][template_name]['start_time'] = time.time()
    while True:
        try:
            p_result = cstdout.readline()
            if first:
                if p_result:
                    log_data.info(str(p_result))
                    first = 0
                    continue
            if p_result:
                log_data.info("ping of [%s] return line:[%s]" % (dst_ip,p_result))
                test_value = get_time_value(p_result)
                log_data.info("ping of [%s] return line:[%s]" % (dst_ip,test_value))
                log_data.info("the count_num of ping:%s" % str(count_num))
                detect_timestamp = int(time.time())
                
                test_result[customer_name][dst_device][template_name]['detect_time'].append(int(test_value))
                test_result[customer_name][dst_device][template_name]['detect_timestamp'].append(detect_timestamp)
                count_num = count_num+1
                test_result[customer_name][dst_device][template_name]['ping_num']=count_num;

                #test_result[customer_name][dst_device][template_name]['end_time'] = time.time()
                print "customer:%s,%s,%s:%s" %(customer_name,dst_device,template_name,test_result[customer_name][dst_device][template_name]['detect_time'])
                print "customer:%s,%s,%s:%s" %(customer_name,dst_device,template_name,test_result[customer_name][dst_device][template_name]['detect_timestamp'])
                #print "customer:%s,%s,%s:%s" %(customer_name,dst_device,template_name,test_result[customer_name][dst_device][template_name]['ping_num'])
                #print "customer:%s,%s,%s:%s" %(customer_name,dst_device,template_name,test_result[customer_name][dst_device][template_name]['start_time'])
                #print "customer:%s,%s,%s:%s" %(customer_name,dst_device,template_name,test_result[customer_name][dst_device][template_name]['end_time'])

                if(test_value == bad_value):
                    continue
            else:
                log_message.error("%s: has recv None, test process exit now ..." % str(cmd))
                try:
                    test_result[customer_name][dst_device][template_name]['start_time'] = None
                    test_result[customer_name][dst_device][template_name]['end_time'] = None
                except:
                    pass
                return
        except Exception,e:
            log_message.error("ping server exit ...error in %s: %s..." % (str(cmd), str(e)))
            trace_err()
            return

def kill_ping(customer_name,dst_device,template_name):
    '''
    kill掉ping
    '''
    log_message.info("start kill_ping")
    try:
        if test_result[customer_name][dst_device][template_name]:
            try:
                test_result[customer_name][dst_device][template_name].terminate()
                test_result[customer_name][dst_devive][template_name].wait()
            except:
                pass
            test_result[customer_name][dst_device][template_name] = None
    except Exception,e:
        log.message.error("error in kill_ping:%s" % str(e))


def restart_sys_ping(customer_name,dst_device,template_name,server_name,dst_ip,ping_interval,pkt_size,timeout):
    '''
    重启ping
    '''
    kill_ping(customer_name,dst_device,template_name)
    test_result[customer_name][dst_device][template_name]['start_time'] = None
    test_result[customer_name][dst_device][template_name]['end_time'] = None
    start_sys_ping_real(customer_name,dst_device,template_name,server_name,dst_ip,ping_interval,pkt_size,timeout)
    

def get_eth_ip(): 
    '''
    Get the local ip
    '''
    try:
        ip_string = sys_command("/sbin/ifconfig eth3 | grep inet\ addr")
        start = ip_string.find("inet addr:")
        if start < 0:
            return []
        ip_str = ip_string[start + len("inet addr:"):]
        ip = ip_str.split()[0]
        return ip
        log_message.info("get the local ip:%s" % str(ip))

    except Exception:
        log_message.error("error in get_eth_ip:%s" % str(e))
        trace_err()
        ip_string = sys_command("/bin/cat /etc/sysconfig/network-scripts/ifcfg-eth3 | grep IPADDR")
        ip_string = ip_string.split('\n')
        ip_string = [line for line in ip_string if '#' not in line]
        ip = ip_string[0].split('=')[1]

        if '"' in ip or '\'' in ip:
            ip = ip[1:-1]
        return ip
  
def get_all_ip(platform):
    '''
    获取本机所有IP
    '''
    ipstr = '([0-9]{1,3}\.){3}[0-9]{1,3}'
    if platform == "Darwin" or platform == "Linux":
        ipconfig_process = subprocess.Popen("ifconfig",stdout = subprocess.PIPE)
        output = ipconfig_process.stdout.read()
        ip_pattern = re.compile('(inet %s)' % ipstr)
        if platform == "Linux":
            ip_pattern = re.compile('(inet addr:%s)' % ipstr)
        pattern = re.compile(ipstr)
        iplist = []
        for ipaddr in re.finditer(ip_pattern,str(output)):
            ip = pattern.search(ipaddr.group())
            if ip.group() != "127.0.0.1":
                iplist.append(ip.group())
        return iplist
    elif platform == "Windows":
        ipconfig_process = subprocess.Popen("ifconfig",stdout= subprocess.PIPE)
        output = ipconfig_process.stdout.read()
        ip_pattern = re.compile("IPv4 Address(\. )*: %s" % ipstr)
        pattern = re.compile(ipstr)
        iplist = []
        for ipaddr in re.finditer(ip_pattern,str(output)):
            ip = pattern.search(ipaddr.group())
            if ip.group() != "127.0.0.1":
                iplist.append(ip.group())
        return iplist

def get_detect_information():
    '''
    获取探测配置
    '''
    pa = platform.system()
    local_ip_list = get_all_ip(pa)
    all_config_dict = get_all_config()
    key = all_config_dict.keys()
    source_iplist = []
    source_namelist = []
    source_serverlist = []
    detect_dict = {}
    all_customer_device_dict = {}
    for d in key:        
        customer_config_dict = all_config_dict[d]
        customer_device_list = customer_config_dict['devicelist']
        source_list = customer_config_dict['sourcelist']
        for source_depth in range(len(source_list)):
             source_namelist = source_list[source_depth]['namelist']
             source_iplist = source_list[source_depth]['iplist']
        detect_device_dict = {}
        all_detect_device_dict = {}
        for depth in range(len(customer_device_list)):
            detect_iplist = customer_device_list[depth]['iplist']
            detect_namelist = customer_device_list[depth]['namelist'] 
            detect_template_name = customer_device_list[depth]['template_name']
            detect_enable = customer_device_list[depth]['detect_enable']
            all_dict = {}
            try:
                for i in range(len(local_ip_list)):
                    local_ip = local_ip_list[i]
                    if local_ip in detect_iplist:
                        index_depth = depth
                        depth_dict = {'depth':index_depth}
                        detect_template_name_dict = {'template_name':detect_template_name}
                        detect_enable_dict = {'detect_enable':detect_enable}
                        device_depth = index_depth + 1

                        if device_depth in range(len(customer_device_list)):
                            device_iplist = customer_device_list[device_depth]['iplist']
                            device_namelist = customer_device_list[device_depth]['namelist']

                        else:
                            device_iplist = source_iplist
                            device_namelist = source_namelist
                        device_dict = {}
                        device_ip_dict = {}               
                        ip_dict = {'ip':device_iplist}
                        device_name_dict = {'name':device_namelist}
                        device_dict.update(ip_dict)
                        device_dict.update(device_name_dict)
                        device_ip_dict = {'device':device_dict}
                        ip_index = detect_iplist.index(local_ip)
                        #detect_dict = {}
                        if len(detect_iplist) == len(detect_namelist):
                            device_name = detect_namelist[ip_index]
                            device_dict = {'name':device_name}
                            all_dict.update(depth_dict)
                            all_dict.update(device_dict)
                            all_dict.update(detect_template_name_dict)
                            all_dict.update(detect_enable_dict)
                            detect_dict = {'detect_device':all_dict}
                        detect_device_dict.update(device_ip_dict)
                        detect_device_dict.update(detect_dict)
                        all_detect_device_dict = {d:detect_device_dict}
                    else:
                        pass
            except Exception,e:
                log_message.error("获取本机ip失败:%" % str(e))
        
        all_customer_device_dict.update(all_detect_device_dict )
    return all_customer_device_dict

if legal == 1:
    detect_information_dict = get_detect_information()
else:
    sys.exit(1)

def detect_device_with_http(customer_name,dst_device,template_name,server_name,device_ip):
    '''
    http探测
    '''
    http_data = None
    detect_time = None
    detect_timestamp = None
    while True:
        t = HttpSendData(server_name,device_ip,request_content,response_content,nameserver,port,int(timeout))
        http_data = t.send_data()
        detect_time = datetime.datetime.now()
        detect_timestamp = int(time.time())
        if http_data[0] != None:
            test_result[customer_name][dst_device][template_name]['detect_time'].append(int(http_data[0]))
        else:
            test_result[customer_name][dst_device][template_name]['detect_time'].append(bad_value)

        test_result[customer_name][dst_device][template_name]['detect_timestamp'].append(detect_timestamp)
        time.sleep(int(detect_interval))
        print "customer:%s,%s,%s:%s" %(customer_name,dst_device,template_name,test_result[customer_name][dst_device][template_name]['detect_time'])
        print "customer:%s,%s,%s:%s" %(customer_name,dst_device,template_name,test_result[customer_name][dst_device][template_name]['detect_timestamp'])



def detect_device_with_tcp(customer_name,dst_device,template_name,server_nmae,device_ip):
    '''
    tcp探测
    '''
    http_data = None
    detect_time = None
    detect_timestamp = None
    while True:
        t =  TcpServer(server_name,device_ip,request_content,response_content,nameserver,int(port),int(timeout))
        http_data = t.SendData()
        detect_time = datetime.datetime.now()
        detect_timestamp = int(time.time())
        if http_data[0] != None:
            test_result[customer_name][dst_device][template_name]['detect_time'].append(int(http_data[0]))
        else:
            test_result[customer_name][dst_device][template_name]['detect_time'].append(bad_value)
        test_result[customer_name][dst_device][template_name]['detect_timestamp'].append(detect_timestamp)
        time.sleep(int(detect_interval))
        print "customer:%s,%s,%s:%s" %(customer_name,dst_device,template_name,test_result[customer_name][dst_device][template_name]['detect_time'])
        print "customer:%s,%s,%s:%s" %(customer_name,dst_device,template_name,test_result[customer_name][dst_device][template_name]['detect_timestamp'])


def sys_ping_monitor_real(customer_name,device_name,template_name,server_name,device_ip,timeout):
    '''
    增加count计时器,判断是否ping,若没有通,增加bad_value
    '''
    oldvalue = test_result[customer_name][device_name][template_name]['ping_num']
    while True:
        time.sleep(int(timeout))
        newvalue = test_result[customer_name][device_name][template_name]['ping_num']
        if (newvalue == oldvalue):
            detect_timestamp = int(time.time())
            test_result[customer_name][device_name][template_name]['detect_time'].append(bad_value)
            test_result[customer_name][device_name][template_name]['detect_timestamp'].append(detect_timestamp)
            print "customer:%s,%s,%s:%s" %(customer_name,device_name,template_name,test_result[customer_name][device_name][template_name]['detect_time'])
            print "customer:%s,%s,%s:%s" %(customer_name,device_name,template_name,test_result[customer_name][device_name][template_name]['detect_timestamp'])

    
def sys_ping_monitor(customer_name,device_name,template_name,server_name,device_ip,timeout):
    '''
    起ping线程
    '''
    try:
        t = threading.Thread(target = sys_ping_monitor_real, args = [customer_name,device_name,template_name,server_name,device_ip,timeout,])
        t.setDaemon(True)
        t.start()
    except Exception,e:
        log_message.error("error in sys_ping_monitor:%s" % str(e))
    

def detect_with_all_device(customer_name,server_name,device_name,device_ip,template_name):
    '''
    根据探测类型调用对应的探测函数，ping,http.tcp探测
    '''
    #server_device_name = server_name + "-----" + device_name

    global test_result
    test_result[customer_name][device_name][template_name]['detect_time'] = []
    test_result[customer_name][device_name][template_name]['detect_timestamp'] = []
    test_result[customer_name][device_name][template_name]['ping_num'] = 0
    #test_result[customer_name][device_name][template_name]['src_device'] = []
    try:
        log_message.info("start to connect to device : %s,device_ip: %s server_name : %s" % (device_name,device_ip,server_name))
        legal_http = template_name.find('http')
        legal_tcp = template_name.find('tcp')
        legal_ping = template_name.find('ping')
        if legal_tcp > 0:
            detect_device_with_tcp(customer_name,device_name,template_name,server_name,device_ip)
        if legal_http > 0:
            detect_device_with_http(customer_name,device_name,template_name,server_name,device_ip)
            
        if legal_ping > 0:
            #sys_ping(customer_name,server_device_name,template_name,server_name,device_ip,detect_interval,pkt_size,timeout)
            sys_ping_monitor(customer_name,device_name,template_name,server_name,device_ip,timeout)
            sys_ping(customer_name,device_name,template_name,server_name,device_ip,detect_interval,pkt_size,timeout)
            #detect_device_with_sys_ping(customer_name,device_name,template_name,server_name,device_ip,detect_interval,pkt_size,timeout) 
    except Exception,e:
        trace_err('error in detect_device_with_http')
        log_message.error("error in detect_device_with_http: %s" % str(e))

        
def checkip(ip):
     p = re.compile('^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$')
     if p.match(ip):
         return True
     else:
         return False

def detect_thread(customer_name,server_name,device_name_list,device_ip_list,template_name):
    '''
    探测线程
    '''
    
    global test_result
    log_message.info("start  detect_thread for %s" % customer_name)

    for ip in device_ip_list:
        ip_index = device_ip_list.index(ip)
        #server_device_name = server_name + "-----" + device_name_list[ip_index]
        dst_device = device_name_list[ip_index]
        test_result[customer_name][dst_device] = {}
        
        for i in range(len(template_name)):
            test_result[customer_name][dst_device][template_name[i]] = {}
            legal = template_name[i].find('ping')

            if legal == -1:
                global response_content
                response_content = all_template_dict[template_name[i]]['response_content']
                global request_content
                request_content = all_template_dict[template_name[i]]['requset_content']

            if legal > 0:
                global pkt_size
                pkt_size = all_template_dict[template_name[i]]['pkt_size']

            global port
            port = all_template_dict[template_name[i]]['port'] 
            global detect_interval
            detect_interval = all_template_dict[template_name[i]]['detect_interval']
            global timeout
            timeout = all_template_dict[template_name[i]]['recv_timeout']
            global detect_type
            detect_type = all_template_dict[template_name[i]]['type'] 

            t_http = threading.Thread(target = detect_with_all_device,args = [customer_name,server_name,device_name_list[ip_index],ip,template_name[i],])
            t_http.setDaemon(True)
            t_http.start()
            #t_http.join()

def detect_customer_thread():
    
    '''
    以客户为基准，调用探测线程进行探测
    '''
    detect_key = detect_information_dict.keys()
    #print detect_key
    global nameserver
    nameserver = report_config_dict['nameserver']
    for d in detect_key:
        global server_name
        server_name = detect_information_dict[d]['detect_device']['name']
        device_name_list = detect_information_dict[d]['device']['name']
        device_ip_list = detect_information_dict[d]['device']['ip']
        global template_name
        template_name = detect_information_dict[d]['detect_device']['template_name']
        detect_enable = detect_information_dict[d]['detect_device']['detect_enable']

        test_result[d]={}
        detect_thread(d,server_name,device_name_list,device_ip_list,template_name)
        

def  http_server_thread_func():

    for d in detect_key:
        try:
            http_server_port = ' '
            http_server = ThreadingHttpServer(('0.0.0.0',http_server_port), WebRequestHandler)
            tid = threading.Thread(target=http_server.serve_forever)
            tid.setDaemon(True)
            tid.start()
        except Exception, e:
            log_message.error("error in http_server_thread_func: %s" % str(e))
   
            
def sleep_time(local_time):
    
    if local_time == None:
        local_time = datetime.datetime.now()
    cur_min = int(local_time.minute)
    cur_sec = int(local_time.second)
    cur_min_sec = cur_min * 60 + cur_sec
    
    return int(report_config_dict["report_interval"]) - (cur_min_sec % int(report_config_dict["report_interval"]))
    
def report_data_clear():
    '''
    Processing of reported data
    '''
    clear_detect_data = None
    clear_interval_data = None
    clear_data_len = None

    try:
        customer_keys = test_result.keys()
        for customer_key in customer_keys:
            device_keys = test_result[customer_key].keys()
            for device_key in device_keys:
                template_keys = test_result[customer_key][device_key].keys()
                for template_key in template_keys:
                    clear_data_len = test_result[customer_key][device_key][template_key]["report_data_len"]    
                    clear_interval_data = test_result[customer_key][device_key][template_key]["detect_timestamp"][clear_data_len:]
                    test_result[customer_key][device_key][template_key]["detect_timestamp"] = clear_interval_data[:]
                    clear_detect_data = test_result[customer_key][device_key][template_key]["detect_time"][clear_data_len:]
                    test_result[customer_key][device_key][template_key]["detect_time"] = clear_detect_data[:]
    except Exception,e:
        log_message.error("error in clear_report_data: %s" % (str(e)))


def get_ldc_start_up_time():
    '''
    获取中央端启动时的时间
    '''
    get_flag = True
    global ldc_start_time
    start_time = None
    agnet_time = None
    for i in range(5):
        try:
            ldc_time = TimeoutServerProxy(uri=DCS,timeout=30,allow_none=True)
            start_time = ldc_time.get_ldc_start_up_time()
            get_flag = True
        except Exception,e:
            agent_time = time.time()
            log_message.error("error in get_ldc_start_up_time:%s" % str(e))
            start_time = agent_time
            get_flag = False

    return start_time

def get_global_config_new():
    '''
    拉取全局配置
    '''
    print "88888"
    try:
        global_config = TimeoutServerProxy(uri=DCS,timeout=30,allow_none=True)
        global_config_dict = global_config.get_global_config()
        print global_config_dict
        return global_config_dict
    except Exception,e:
        log_message.error("error in get_global_config_new:%s" % str(e))

   

def get_agent_start_up_time():
    
    '''process detect start up?
       if start up return start up time
    '''
    start_time = None
    pid = p_running("detect")
    if pid > 0:
        start_time = int(time.time())
    return start_time

        
def report_data_preparation():
    '''
    准备上报数据
    '''
    report_data = [] 
    detect_data = None
    detect_interval_data = None
    detect_data_len = None
    customer_dict = {}
    dst_dict = {}
    template_name_dict = {}
    detect_len_dict = {}
    detect_time_dict = {}
    detect_timestamp_dict = {}
    report_customer_dict = {}
    try:
        customer_keys = test_result.keys() 
        if (len(customer_keys)) == 0:
            log_message.error(0,"no data to report")
            return None
        log_data.info("before report process,the test result is:%s" % str(test_result))
        for customer_key in customer_keys:
            device_keys = test_result[customer_key].keys()
            for device_key in device_keys:
                template_keys = test_result[customer_key][device_key].keys()
                for template_key in template_keys:
                    detect_data_list = test_result[customer_key][device_key][template_key]["detect_time"]
                    #print detect_data_list
                    detect_data_len = len(detect_data_list)
                    detect_interval_list = test_result[customer_key][device_key][template_key]["detect_timestamp"]
                    try:
                        if (detect_data_len >= 1000):
                            detect_data_len = 800
                            detect_data_tmp = test_result[customer_key][device_key][template_key]["detect_time"][-detect_data_len:]
                            test_result[customer_key][device_key][template_key]["detect_time"] = detect_data_tmp[:]
                            detect_interval_tmp = test_result[customer_key][device_key][template_key]["detect_timestamp"][-detect_data_len:]
                            test_result[customer_key][device_key][template_key]["detect_timestamp"] = detect_interval_tmp[:]
                    except:
                        pass
                    try:
                        detect_data = test_result[customer_key][device_key][template_key]["detect_time"][:]
                        detect_interval_data = test_result[customer_key][device_key][template_key]["detect_timestamp"][:]
                        test_result[customer_key][device_key][template_key]["report_data_len"] = len(detect_data)
                    except Exception,e:
                        log_message.error("error in report func : %s" % str(e))
                        continue
                    customer_dict = {'customer':customer_key}
                    dst_dict = {'dst_device':device_key}
                    template_name_dict = {'template_name':template_key}
                    detect_len_dict = {'detect_len':detect_data_len}
                    detect_time_dict = {'detect_time':detect_data}
                    detect_timestamp_dict  = {'detect_timestamp':detect_interval_data}
                    global src_name_dict
                    src_name_dict = {'src_device':server_name}
                    report_customer_dict.update(customer_dict)
                    report_customer_dict.update(dst_dict)
                    report_customer_dict.update(template_name_dict)
                    report_customer_dict.update(detect_len_dict)
                    report_customer_dict.update(detect_time_dict)
                    report_customer_dict.update(detect_timestamp_dict)
                    report_customer_dict.update(src_name_dict)
                    #report_data = {customer_key:report_customer_dict}
                    #report_data.append([customer_key,device_key,template_key,detect_data,detect_interval_data,detect_data_len,agent_ldc_offsent_dict,src_name_dict])
                    #report_data.append([customer_dict,dst_dict,template_name_dict,detect_time_dict,detect_timestamp_dict,detect_len_dict,agent_ldc_offsent_dict,src_name_dict])
                    #global src_name_dict
                    #src_name_dict = {'src':server_name}
                    #report_data.append([test_result,agent_ldc_offsent_dict,src_name_dict])
        #report_data.append([test_result,agent_ldc_offsent_dict,src_name_dict])
        report_data.append(test_result)
        report_data.append(agent_ldc_offsent_dict)
        report_data.append(src_name_dict)

        log_data.info("prepare to report data,the report_data is:%s" % str(report_data))
        return report_data
    except Exception,e:
        log_message.error("error in report_data_preparation: %s" % (str(e)))
        trace_err()
        return []


def report_func():
    '''report test result to LDC'''
    report_result = None
    report_flag = True

    while True:
        try:
            local_time = datetime.datetime.now()
            cur_min = int(local_time.minute)
            cur_sec = int(local_time.second)
            cur_min_sec = cur_min * 60 + cur_sec
        
            log_message.info("report time...(%d:%d = %d) %d = %d" % (cur_min,cur_sec,cur_min_sec,int(report_config_dict["report_interval"]),cur_min_sec % int(report_config_dict["report_interval"])))
            time.sleep(int(report_config_dict["report_interval"]))
            if report_result == None:
                report_result = report_data_preparation()
                if report_result == None:
                    continue
            log_data.info("start to report to LDC:%s %s" % (DCS,str(report_result)))
            if report_config_dict["report_addr"] == None:
                log_message.info("DCS ip  is not known ...")
                report_result = None
                time.sleep(30)
                continue
            for i in range(5):
                try:
                    report_s = TimeoutServerProxy(uri=DCS,timeout=30,allow_none=True)
                    echo_msg = report_s.echo_ldc()
                    if (echo_msg != "listening"):
                        log_message.warn("report to LDC echo : %s msg: %s is not listening, try later ..." % (DCS, echo_msg))
                        time.sleep(3)
                        continue
                    if (report_s.report_to_ldc(report_result)):
                        report_flag = True
                        log_message.info("report to LDC success : %s ..." % DCS)
                        break
                    else:
                        report_flag = False
                        log_message.warn("report to LDC echo : %s msg: %s is not listening, try later ..." % (DCS, echo_msg))
                        break
                except Exception,e:
                    log_message.error("report faild...report to LDC syserror : %s :%s" % (DCS, str(e)))
                    time.sleep(3)
                    report_flag = False
            if report_flag == True:
                report_data_clear()
            report_result = None
            time.sleep(30)
        except Exception,e:
            trace_err()
            report_result = None
            log_message.error("report to LDC syserror : %s :%s" % (DCS, str(e)))
            time.sleep(30)
        
        
def report_thread_func():
    
    '''start the report thread'''
    log_message.info("start report thread :%s " % DCS)
    try:
        global main_thread_info
        tid = threading.Thread(target = report_func)
        tid.setDaemon(True)
        main_thread_info["report_ldc_thread"] = tid
        tid.start()

    except Exception,e:
        trace_err("report_thread_func")
        log_message.error("error in report_thread_func:%s" % str(e))


def get_offsent():
    '''
    获取LDC端和agent端时间偏差
    '''
    ldc_start_time = None
    agent_time = None
    global agent_ldc_offsent
    global agent_ldc_offsent_dict
    ldc_start_time = get_ldc_start_up_time()
    agent_time = get_agent_start_up_time()
    agent_ldc_offsent = agent_time - ldc_start_time
    agent_ldc_offsent_dict = {'offsent':agent_ldc_offsent}
    print agent_ldc_offsent_dict
    time.sleep(300)


def get_offsent_thread_func():
    '''
    获取中央端与探测端时间差值
    '''
    log_message.info("start get_offsent_thread_func")
    try:
        tid = threading.Thread(target = get_offsent)
        tid.setDaemon(True)
        tid.start()
    except Exception,e:
        trace_err("get_offsent_thread_func")
        log_message.error("error in get_offsent_thread_func:%s" %str(e))


if __name__ == '__main__':

   try:
       opts,args = getopt.getopt(sys.argv[1:],"vdq")
   except getopt.GetoptError:
       print "illegal option(s) -- " + str(sys.argv[1:])  

   for name,value in opts:
       if ( name == "-v" ):
           log_message.info("打印版本:%s" %  str(VERSION))
           sys.exit(0)
       if ( name == "-d" ):
           DEBUG = 1
       if ( name == "-q" ):
           QUIET = 1

   python_daemon()

   ip =  get_eth_ip()
   ip_postion = get_detect_information() 
   ldc_time = get_ldc_start_up_time()
   agent_time = get_agent_start_up_time()
   try:
       pid = os.getpid()
       p_f = open(PID_FILE,'w')
       p_f.write(str(pid))
       p_f.close()

   except IOError,e:
       log_message.error(str(e))
       os._oxit(1)
   detect_customer_thread()
   get_offsent_thread_func()
   report_thread_func()
   #get_offsent_thread_func()
   while True:
       time.sleep(600)






   

