#!/usr/bin/env python
# -*- coding: utf-8 -*-



###############################################################################
# function:Analytical profile and determine the legality of the configuration file
#
#
# Author:wenbin.pu <wenbin.pu@chinacache.com>
#
#
# date:2016.8.20
##############################################################################

import os
import string
import  ConfigParser
import socket
import sys
import re
from detect_log import *
from SimpleXMLRPCServer import SimpleXMLRPCServer


try:
    cf = ConfigParser.ConfigParser()
    cf = ConfigParser.RawConfigParser()
    cf.read("/root/TTA_detect/config/detector.cfg")
    sec = cf.sections()
except Exception,e:
    log_message.error("the path of configure error:%s" % str(e))



def default_resolve_dns_list(domain_name_list):
    
    IPs = {}
    ip_list = []
    server_ip_dict = {}
    ip_dict = {}

    log_message.info("current local config is: %s" % daomain_name_list);

    for host in server_list:
        results = socket.getaddrinfo(host,None)
        for result in results:
            if ip_list.count(result[4][0]) == 0:
                ip_list.append(result[4][0])
                IPs[result[4][0]] = host
        server_ip_dict = {host:ip_list}
        ip_dict.update(server_ip_dict)

    return ip_dict    


def default_resolve_dns(domain_name):
    '''
    域名解析：采用系统默认的nameserver
    '''
    IPs = {}
    ip_list = []
    server_ip_dict = {}
    ip_dict = {}
    results = socket.getaddrinfo(server,None)
    for result in results:
        if ip_list.count(result[4][0]) == 0:
            ip_list.append(result[4][0])
            IPs[result[4][0]] = server
        else:
            continue
        server_ip_dict = {server:ip_list}
        ip_dict.update(server_ip_dict)

    return ip_dict


def reply_to_iplist(data):
    if isinstance(data, basestring)== True:
        iplist = ['.'.join(str(ord(x)) for x in s) for s in re.findall('\xc0.\x00\x01\x00\x01.{6}(.{4})', data) if all(ord(x) <= 255 for x in s)]
    else:
         iplist = []
    return iplist

def domain_to_ip(dnsserver,domain_name):
    iplist = []
    seqid = os.urandom(2)
    host = ''.join(chr(len(x))+x for x in domain_name.split('.'))
    #print str(host)
    data = '%s\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00%s\x00\x00\x01\x00\x01' % (seqid, host)
    sock = socket.socket(socket.AF_INET,type=socket.SOCK_DGRAM)
    server_ip_dict = {}
    try:
         sock.settimeout(10)
         sock.sendto(data, (dnsserver, 53))
         data = sock.recv(512)
         iplist = reply_to_iplist(data)
         return iplist

    except Exception,e:
         
         return iplist
         log_message.error("Error in domain_to_ip : %s" % str(e))

         sock.close

def resolve_dns_list(domain_name_list):
    global_dns_dict = get_global_config()
    dns_server_list = global_dns_dict['nameserver']
    #print dns_server_list
    server_ip_dict = {}
    ip_dict = {}
    for domain in server_list:
        for dns in dns_server_list: 
            dns_ip = domain_to_ip(dns,domain)
            if len(dns_ip) > 0:
                server_ip_dict = {domain:dns_ip}
                ip_dict.update(server_ip_dict)
                break
    return ip_dict


def resolve_dns(domain_name):
    '''
    域名解析：自己配置nameserver
    '''
    global_dns_dict = get_global_config()
    dns_server_list = global_dns_dict['nameserver']
    server_ip_dict = {}
    ip_dict = {}
    for dns in dns_server_list:
        dns_ip = domain_to_ip(dns,domain_name)
        #print dns_ip
        if len(dns_ip) > 0:
            server_ip_dict = {domain_name:dns_ip}
            ip_dict.update(server_ip_dict)
            print ip_dict 
            break
        else:
            pass
    return server_ip_dict
    
    
def get_global_config():
    '''
    获取全局配置:nameserver,s上报地址、端口、时间间隔
    '''
    global_config_dict = {}

    if cf.options('global'):
        if cf.has_option('global','report_addr'):
            report_addr = cf.get("global","report_addr")
        else:
            report_addr = ' '
        report_addr_dict = {'report_addr':report_addr}

        if cf.has_option('global','nameserver'):
            nameserver = cf.get('global','nameserver').split(',')
        else:
            nameserver = []
        nameserver_dict = {'nameserver':nameserver}

        if cf.has_option('global','report_interval'):
            report_interval = cf.get('global','report_interval')
        else:
            report_interval = ' '

        if cf.has_option('global','report_port'):
            report_port = cf.get('global','report_port')
        else:
            report_port = ' '
        report_port_dict = {'report_port':report_port}
        report_interval_dict = {'report_interval':report_interval}
        global_config_dict.update(report_addr_dict)
        global_config_dict.update(nameserver_dict)
        global_config_dict.update(report_interval_dict)
        global_config_dict.update(report_port_dict)

        #log_message.info("global configuration:%s" % str(global_config_dict))
        return global_config_dict

def get_customer():
    '''
    获取客户字段
    '''
    customer_list = []
    try:
        for customer in enumerate(sec):
            try:
                if cf.has_option('customer','customer'):
                    customer_list = cf.get("customer","customer").split(',')
                else:
                    customer_list = []
                return customer_list
            except Exception,e:
                pass
    except Exception,e:
        print e

def get_customer_name():
    '''
    拼接customer与客户名称
    '''
    name_list = get_customer()
    customer_name_list = []
    for i in range(len(name_list)):
        customer_name = 'customer' + '_' + name_list[i]
        customer_name_list.append(customer_name)
    return customer_name_list

def get_all_config():
    '''
    获取每一个客户的设备组、设备信息,源站、所用的探测模板，最后以字典的形式保存
    '''
    customer_name_list = get_customer_name()
    global_dns_name_dict = get_global_config()
    dns_name_list = global_dns_name_dict['nameserver']
    all_dict = {}

    for i in range(len(customer_name_list)):
        if cf.has_option(customer_name_list[i],'level_depth'):
            level_depth = cf.get(customer_name_list[i],'level_depth')
        else:
            level_depth = ' '

        if cf.has_option(customer_name_list[i],'detect_template'):
            detect_template = cf.get(customer_name_list[i],'detect_template').split(',')
        else:
            detect_template = []
        
        if cf.has_option(customer_name_list[i],'detect_enable'):
            detect_enable = cf.get(customer_name_list[i],'detect_enable')
        else:
            detect_enable = '1'

        if cf.has_option(customer_name_list[i],'source_devicelist'):
            source_device_list = cf.get(customer_name_list[i],'source_devicelist').split(',')
        else:
            source_device_list = []
        source_devicelist_dict = {'namelist':source_device_list}

        if cf.has_option(customer_name_list[i],'source_deviceip'):
            source_deviceip_list = cf.get(customer_name_list[i],'source_deviceip').split(',')
        else:
            source_deviceip_list = []

        if cf.has_option(customer_name_list[i],'source_servername'):
            source_servername_list = cf.get(customer_name_list[i],'source_servername').split(',')
        else:
            source_servername_list = []

        if len(source_deviceip_list ) > 0:
            source_deviceip_dict = {'iplist': source_deviceip_list}
        else:
            source_deviceip_dict = {'iplist': source_servername_list}

        source_detect_template_dict = {'template_name': None}
        source_detect_enable_dict = {'detect_enable':0}
        #source_servername_dict = {'servernamelist':source_servername_list}
        source_dict = {}
        source_list = []
        all_source_dict = {}
        source_dict.update(source_detect_template_dict)
        source_dict.update(source_detect_enable_dict)
        source_dict.update(source_devicelist_dict)
        source_dict.update(source_deviceip_dict)

        '''
        if len(source_deviceip_dict['iplist']) > 0:
            source_dict.update(source_deviceip_dict)
        else:
            source_dict.update(source_servername_dict)
        '''
        source_list.append(source_dict)
        all_source_dict = {'sourcelist':source_list}
        customer_device_list = []
        all_customer_device_dict = {}
        all_device_dict_tmp = {}
        all_device_dict = {}
        source_customer_device_dict = {}

        for j in range(int(level_depth)):
            customer_level = customer_name_list[i] + '_' + 'level_' + str(j) + '_' + 'device'
            level_devicelist = 'level' + '_' + str(j) + '_' + 'devicelist'
            level_deviceip = 'level' + '_' + str(j) + '_' + 'deviceip'
            customer_device_dict = {}

            if cf.has_option(customer_name_list[i],level_devicelist):
                level_device_list = cf.get(customer_name_list[i],level_devicelist).split(',')
            else:
                level_device_list = []
            level_device_dict = {'namelist':level_device_list}

            if cf.has_option(customer_name_list[i],level_deviceip):
                level_deviceip_list = cf.get(customer_name_list[i],level_deviceip).split(',')
            else:
                level_deviceip_list = []
            level_deviceip_dict = {'iplist':level_deviceip_list}
            new_detect_template_dict = {}
            new_detect_enable_dict = {}
            
            if cf.has_option(customer_level,'detect_template'):
                new_detect_template = cf.get(customer_level,'detect_template').split(',')
            else:
                new_detect_template = detect_template
            new_detect_template_dict = {'template_name': new_detect_template}

            if cf.has_option(customer_level,'detect_enable'):
                new_detect_enable = cf.get(customer_level, 'detect_enable')
            else:
                new_detect_enable = detect_enable
            new_detect_enable_dict = {'detect_enable': new_detect_enable}
            customer_device_dict.update(new_detect_template_dict)
            customer_device_dict.update(new_detect_enable_dict)
            customer_device_dict.update(level_deviceip_dict)
            customer_device_dict.update(level_device_dict)
            customer_device_list.append(customer_device_dict)
            all_customer_device_dict = {'devicelist':customer_device_list}
            source_customer_device_dict.update(all_customer_device_dict)
            source_customer_device_dict.update(all_source_dict)
        all_device_dict = {customer_name_list[i]:source_customer_device_dict}
        all_dict.update(all_device_dict)

    log_message.info("all device information:%s" % str(all_dict))
    return all_dict


def get_template_old():
    '''
    获取探测模板具体信息：请求内容，响应内容，探测时间间隔，端口号，ping包的大小
    '''
    if cf.has_option('detect_template','template'):
        template_list = cf.get('detect_template','template').split(',')
    else:
        template_list = []

    if cf.has_option('detect_template','detect_port'):
        detect_port = cf.get('detect_template','detect_port')
    else:
        detect_port = ' '

    if cf.has_option('detect_template','detect_recv_timeout'):
        detect_recv_timeout = cf.get('detect_template','detect_recv_timeout')
    else:
        detect_recv_timeout = ' '

    if cf.has_option('detect_template','detect_interval'):
        detect_interval = cf.get('detect_template','detect_interval')
    else:
        detect_interval = ' '
    all_template_dict = {}
    for i in range(len(template_list)):
        template_name = 'detect_template' + '_' + template_list[i]

        if cf.has_option(template_name,'type'):
            type_name = cf.get(template_name,'type')
        else:
            type_name = ' '
        type_name_dict = {'type':type_name}

        if cf.has_option(template_name,'pkt_size'):
            pkt_size = cf.get(template_name,'pkt_size')
        else:
            pkt_size = ' '
        pkt_size_dict = {'pkt_size':pkt_size}

        if cf.has_option(template_name,'request_content'):
            request_content = cf.get(template_name,'request_content')
        else:
            request_content = ' '
        request_content_dict = {'requset_content':request_content}

        if cf.has_option(template_name,'response_content'):
            response_content = cf.get(template_name,'response_content')
        else:
            response_content = ' '
        response_content_dict = {'response_content':response_content}

        if cf.has_option(template_name,'detect_port'):
            port = cf.get(template_name,'detect_port')
        else:
            port = detect_port
        port_dict = {'port':port}

        if cf.has_option(template_name,'detect_recv_timeout'):
            recv_timeout = cf.get(template_name,'detect_recv_timeout')
        else:
            recv_timeout = detect_recv_timeout
        recv_timeout_dict = {'recv_timeout':recv_timeout}

        if cf.has_option(template_name,'detect_interval'):
            interval = cf.get(template_name,'detect_interval')
        else:
            interval = detect_interval
        interval_dict = {'detect_interval':interval}
        template_dict = {}
        template_dict.update(type_name_dict)
        template_dict.update(request_content_dict )
        template_dict.update(response_content_dict)
        template_dict.update(port_dict)
        template_dict.update(recv_timeout_dict)
        template_dict.update(interval_dict)
        template_dict.update(pkt_size_dict)
        template_name_dict = {template_list[i]:template_dict}
        all_template_dict.update(template_name_dict)
    
    log_message.info("探测模板信息:%s" % str(all_template_dict))
    return all_template_dict


def get_template():
    '''
    ping 探测模板中去掉请求和响应内容,http和tcp探测模板中过滤掉包的大小
    '''
    template_dict = get_template_old()
    template_keys = template_dict.keys()
    for d in template_keys:
        legal = d.find('ping')
        if legal > 0:
            template_dict[d].pop('requset_content')
            template_dict[d].pop('response_content')
        if legal == -1:
            template_dict[d].pop('pkt_size')

    return template_dict

JUDGMENT_SAFETY = 1

def judgment__safety():
    '''
    判断配置文件的哈法性，合法返回1
    '''

    global_config_dict = get_global_config()
    all_config_dict = get_all_config()
    all_template_dict = get_template()
    #print all_template_dict
    JUDGMENT_SAFETY = 1

    if global_config_dict['report_addr'] is ' ':
        log_message.error("report_address is not configured.... get report_add for report:[%s] " % (global_config_dict['report_addr']))
        JUDGMENT_SAFETY = 0

    config_key = all_config_dict.keys()
    for d in config_key:
        for i in range(len(all_config_dict[d]['devicelist'])):
            #print len(all_config_dict[d]['devicelist'][i]['namelist'])
            if (all_config_dict[d]['devicelist'][i]['template_name']  == []):
                log_message.error("i :%d d:%s error in template_name is not configured ...,i represents the device layers,d represents customer" % (i,d))
                JUDGMENT_SAFETY = 0

            if (all_config_dict[d]['devicelist'][i]['namelist'] == []) or (all_config_dict[d]['devicelist'][i]['iplist'] == []):
                log_message.error("i :%d d:%s error in device_name or device_ip is not configured ...,i represents the device layers,d represents customer" % (i,d))
                JUDGMENT_SAFETY = 0

            if len(all_config_dict[d]['devicelist'][i]['namelist']) is not len(all_config_dict[d]['devicelist'][i]['iplist']):
                log_message.error("i :%d d:%s error in the length of device_name is not equal the length of device_name ,device_name or device_ip is not configured ...,i represents the device layers,d represents customer" % (i,d))
                JUDGMENT_SAFETY = 0
        for j in range(len(all_config_dict[d]['sourcelist'])):
            if (all_config_dict[d]['sourcelist'][j]['namelist'] == []) or (all_config_dict[d]['sourcelist'][j]['iplist'] == []):
                log_message.error(" d:%s error in source_name is not configured " % (d))
                JUDGMENT_SAFETY = 0

            if len(all_config_dict[d]['sourcelist'][j]['namelist']) is not len(all_config_dict[d]['sourcelist'][j]['iplist']):
                 log_message.error(" d:%s error in the length of the source_name is not equal the length of ip ,source_name or source_ip is not configured ...," % (d))
                 JUDGMENT_SAFETY = 0
    template_key = all_template_dict.keys()

    for m in template_key:
        legal = m.find('ping')
        if legal == -1:
            if all_template_dict[m]['requset_content'] is ' ':
                log_message.error(" m:%s error in request_content is not configured ...," % (m))
                JUDGMENT_SAFETY = 0

            if all_template_dict[m]['response_content'] is ' ':
                log_message.error(" m:%s error in response_content is not configured ...," % (m))
                JUDGMENT_SAFETY = 0

        if legal > 0:
            if all_template_dict[m]['pkt_size'] is ' ':
                log_message.error(" m:%s error in pkt_size is not configured ...," % (m))
                JUDGMENT_SAFETY = 0

        if all_template_dict[m]['detect_interval'] is ' ':
            log_message.error(" m:%s error in detect_interval is not configured ...," % (m))
            JUDGMENT_SAFETY = 0

        if all_template_dict[m]['port'] is ' ':
            log_message.error(" m:%s error in port is not configured ...," % (m))
            JUDGMENT_SAFETY = 0

        if all_template_dict[m]['type'] is ' ':
            log_message.error(" m:%s error in type is not configured ...," % (m))
            JUDGMENT_SAFETY = 0
        
    return JUDGMENT_SAFETY 


    
if __name__ == '__main__':

   customer = get_customer()
   customer_name = get_customer_name()

   global_config = get_global_config()
   print global_config

   config =  get_all_config()
   #print config

   template = get_template_old()
   #print template

   new_template = get_template()
   print new_template



   ip = resolve_dns('www.baidu.com')
   #print ip

   safety = judgment__safety()
   print safety
    
   '''
   domainlist = ['www.baidu.com','www.qq.com']
   serverlist = ['8.8.8.8','114.114.114.14']

   server_ip_dict = {}
   for domain in domainlist:
       for dns in serverlist:
           ip = domain_to_ip(dns,domain)
           print ip
           if len(ip) > 0:
               ip_dict = {domain:ip}
               print ip_dict
               server_ip_dict.update(ip_dict)
               break
               
   print server_ip_dict 

   '''






