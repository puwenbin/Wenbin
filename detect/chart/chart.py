#!/usr/bin/env python
# -*- coding: utf-8 -*-

from detect_config import *
import datetime
import time
import MySQLdb
import getopt
import os
import sys
import shutil
from chart_log import *
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
from pylab import *
import dateutil, pylab,random
from matplotlib.dates import AutoDateLocator, DateFormatter
import pylab as pl
import resource
from commands import getoutput


DEFAULT_HISTORY_TIME = 5      # 1 day
DEFAULT_LEFT_MAGIN = 600      # 600 s
DEFAULT_TIME_INTERVAL = 3600.0  # 3600 s

DEFAULT_TINE = 7200
dbconn = None

VERSION='0.1.0'
DEBUG = 0
QUIET = 0

if (hasattr(os,"devnull")):
    NULL_DEVICE = os.devnull
else:
    NULL_DEVICE = "/dev/null"


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
    os.open(NULL_DEVICE,os.O_RDWR)
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

        
def filterline(linedata):
    linedata = linedata.strip()
    linedata = linedata.strip('[]')
    linedata = linedata.strip()
    return linedata

def get_real_monitor_data(customername,srcdevice,dstdevice,template_lst):
    monitor_data = []
    table_name = "customer_"+customername

    searchtime = datetime.datetime.now()-datetime.timedelta(hours=DEFAULT_HISTORY_TIME)

    cursor = dbconn.cursor()
    for monitor_template in template_lst:
        sql = "select id,detect_timestmap,detect_value from %s where first_data_timestamp > '%s' and src_device='%s' and dst_device='%s' and template_name='%s'" %(table_name,searchtime,srcdevice,dstdevice,monitor_template.templatename)
        log_message.info("sql:%s" % str(sql))
        template_data = {}
        template_data['name'] = monitor_template.templatename
        template_data['type'] = monitor_template.templatetype
        template_data['detect_timestamp'] = []
        template_data['detect_value'] = []

        timestamp = []
        valuelist = []

        cursor.execute(sql)
        results = cursor.fetchall()
        for row in results:
            tmpstamp = row[1]
            tmpstamp = filterline(tmpstamp)
            tmpvalue = row[2]
            tmpvalue = filterline(tmpvalue)
            try:
                tmpstamp = tmpstamp.split(',')
                tmpstamp = map(lambda x:int(x),tmpstamp)

                tmpvalue = tmpvalue.split(',')
                tmpvalue = map(lambda x:int(x),tmpvalue)

                timestamp.extend(tmpstamp)
                valuelist.extend(tmpvalue)
 
            except Exception,e:
                log_message.error("error record with id :%s " % str(e))
                continue

        template_data['detect_timestamp'] = timestamp
        template_data['detect_value'] = valuelist

        monitor_data.append(template_data)
        
    return (monitor_data,searchtime)



def adjust_timelst(timelst,searchleft):
    for i in range(len(timelst)):
        timelst[i] = (timelst[i]-searchleft)/DEFAULT_TIME_INTERVAL

def calc_average(valuelst):
    alpha = 0.9
    aver = 0

    for x in valuelst:
        if aver == 0:
            aver = x
        else:
            aver = float(aver*alpha+(1-alpha)*x)
    return aver

def adjust_chart_data(monitor_data,searchtime):
    searchleft = datetime.datetime(searchtime.year,searchtime.month,searchtime.day,searchtime.hour,0,0)
    searchleft = int(time.mktime(searchleft.timetuple()))
    
    for monitor in monitor_data:
        timelst = monitor['detect_timestamp']
        valuelst = monitor['detect_value']

        if len(timelst) == 0:
            continue

        first_time = timelst[0]
        first_data = valuelst[0]

        adjust_timelst(timelst,searchleft)
        aver = calc_average(valuelst)
        '''   
        if first_time-searchleft > DEFAULT_LEFT_MAGIN:
            timelst.insert(0,(first_time-searchleft)/DEFAULT_TIME_INTERVAL)
            valuelst.insert(0,0)
            timelst.insert(0,0)
            valuelst.insert(0,0)
        else:
            timelst.insert(0,0)
            valuelst.insert(0,first_data)
        '''

        monitor['aver_detect_value']=aver


def get_yes_time():
    '''
    从当前时间开始取前5个小时的时间值
    '''
    now_time = datetime.datetime.now()
    now_hour = time.strftime('%H',time.localtime(time.time()))
    now_yes_time_list = []
    for i in range(0,6):
        now_yes_time = now_time + datetime.timedelta(hours = -i)
        now_yes_hour = now_yes_time.strftime("%H")
        now_yes_time_list.append(int(now_yes_hour))
    now_yes_time_list.reverse()
    return now_yes_time_list


def gen_chart_with_data(customer,src_dev,dst_dev,name,monitor_data):
    '''
    实现了从当前时间开始取前5个小时的数据缩略图
    '''
    font = {'family':'serif','color':'darkred','size':20}    
    mpl.rcParams['font.sans-serif']=['SimHei']
    mpl.rcParams['axes.unicode_minus']=False 
    #font_size=30
    ax_new = None
    timestamp = []
    value = []
    time_value = None
    x_lables = None
    y_lables = None
    y_value = None

    aver = 0
    low_level = 0.0
    high_level = 50.0
    max_value = 0.0

    time_value = get_yes_time()
    x_lables = time_value

    fig = plt.figure(figsize=(8,6), dpi=96, facecolor="white")
    xmajorFormatter = FormatStrFormatter('%5.1f')
    ymajorFormatter = FormatStrFormatter('%1.1f')

    monitor_data_len = len(monitor_data)
    tm = time.localtime(time.time())
    local_time = time.strftime("%Y-%m-%d %H:%M:%S",tm)

    if monitor_data_len > 0:
        for i in range(monitor_data_len):
            ax = 'ax' + str(i+1)
            if "detect_value" in monitor_data[i]:
                value = monitor_data[i]["detect_value"]
                if len(value) > 0:
                    max_value = max(monitor_data[i]["detect_value"])
                else:
                    max_value = 0.0
            else:
                value = []
                max_value = 0.0
            if "detect_timestamp" in monitor_data[i]:
                timestamp = monitor_data[i]["detect_timestamp"]

            lable_value = monitor_data[i]["type"]
            ax = fig.add_subplot(2,1,i+1)
            ax.plot(timestamp,value,'-',color='lime',linewidth=2)
            #plt.fill_between(timestamp,y,value,facecolor='lime')
            ax.xaxis.labelpad = 40
            ax.yaxis.labelpad = 40

            ax.xaxis.set_major_formatter(xmajorFormatter)  
            ax.yaxis.set_major_formatter(ymajorFormatter)
            #ax.set_xticks(x_value_actual)
            #ax.set_xticklabels(x_lables,rotation=40,fontsize='small') 
            ax.set_xticklabels(x_lables,fontsize=20) 

            if "aver_detect_value" in monitor_data[i]: 
                aver = monitor_data[i]["aver_detect_value"]

                if ((aver < 10.0) and (max_value <  (10*aver))):
                    low_level = aver*0.5
                    high_level = aver *10
                if ((aver < 10.0) and (max_value > (10*aver))):
                    low_level = aver*0.5
                    high_level = aver *25
                
                if ((aver > 10.0) and (max_value < (2*aver))):
                    low_level = aver*0.5
                    high_level = aver *2
                
                if ((aver > 10.0) and (max_value in range(int(2*aver),int(3*aver)))):
                    low_level = aver*0.5
                    high_level = aver *3
                if ((aver > 10.0) and (max_value in range(int(3*aver),int(4*aver)))):
                    low_level = aver*0.5
                    high_level = aver *4
        
                if ((aver > 10.0) and (max_value in range(int(4*aver),int(5*aver)))):
                    low_level = aver*0.5
                    high_level = aver *5
                if ((aver > 10.0) and (max_value > 5*aver)):
                    low_level = aver*0.5
                    high_level = aver *20
                if aver == 2000.0:
                    low_level = aver*0.5
                    high_level = aver*1.5
            else:
                low_level=0.0
                high_level=50.0

            y_lables = [int(low_level),int(aver),int(high_level)]
            y_value = [low_level,aver,high_level]
            ax.set_ylim(int(low_level),int(high_level))
    
            title_name = lable_value + '_' + local_time + '_' + str(i)
            ax.set_title(title_name,fontdict = font)
            ax.xaxis.grid(True, which='major')
    else:
        y_lables = [0,25,50]
        timestamp = []
        value = []
        ax1 = fig.add_subplot(1,1,1)
        lable_value = 'NULL'
        ax1.plot(timestamp,value,'-',color='lime')
        ax1.xaxis.labelpad = 40
        ax1.yaxis.labelpad = 40
        ax1.xaxis.set_major_formatter(xmajorFormatter)
        ax1.yaxis.set_major_formatter(ymajorFormatter)
        ax1.set_xticks(x_value_actual)
        ax1.set_xticklabels(x_lables,rotation=40,fontsize=20)
        ax1.set_yticklabels(y_lables,fontsize=14)        
        title_name = lable_value + '_' + local_time + '_' + str(i)
        ax1.set_title(title_name)
        ax1.xaxis.grid(True, which='major')

    plt.grid()
    plt.legend()
    plt.show()
    pl.subplots_adjust(left=0.08, right=0.99, wspace=0.25, hspace=0.45)
    #path = '/root/app/detect/app/picture/'

    path = '/tmp/picture/'
    isExists=os.path.exists(path)
    if not isExists:
        os.makedirs(path)

    path_name = os.path.join(path,name)

    save_start = datetime.datetime.now()

    plt.savefig(path_name,dpi=80)

    save_end = datetime.datetime.now()
    save_time_sec = (save_end-save_start).seconds
    save_time_mic = (save_end-save_start).microseconds
    save_time = save_time_sec *1000 + save_time_mic /1000



def gen_dev_chart(customername,src_dev,dst_dev,template_lst):
    
    monitor_data,searchtime = get_real_monitor_data(customername,src_dev,dst_dev,template_lst)
    adjust_chart_data(monitor_data,searchtime)
    return monitor_data



def gen_all_chart(customer_list):
    '''
    根据客户,源和目的画出缩略图
    '''

    for cus in customer_list:
        level_depth = cus.level_depth
        for i in range(level_depth-1):
            src_lst = cus.levellist[i].devicelist
            dst_lst = cus.levellist[i+1].devicelist

            for src_dev in src_lst:
                for dst_dev in dst_lst:
                    sql_start = datetime.datetime.now()
                    monitor_data = gen_dev_chart(cus.customername,src_dev,dst_dev,cus.levellist[i].detecttemplate_lst)
                    sql_end = datetime.datetime.now()
                    sql_time_sec = (sql_end-sql_start).seconds
                    sql_time_mic = (sql_end-sql_start).microseconds
                    sql_time = sql_time_sec * 1000 + sql_time_mic /1000
                    #print "sql_time:%s,%s,%s,%s" % (str(sql_time),cus.customername,src_dev,dst_dev)
                    log_data.info("sql_time:%s,%s,%s,%s" % (str(sql_time),cus.customername,src_dev,dst_dev))

                    name = cus.customername + '_' + src_dev + '_' + dst_dev + '.png'
                    chart_start = datetime.datetime.now()
                    gen_chart_with_data(cus.customername,src_dev,dst_dev,name,monitor_data)
                    chart_end = datetime.datetime.now()
                    chart_time_sec = (chart_end-chart_start).seconds
                    chart_time_mic = (chart_end-chart_start).microseconds
                    chart_time = chart_time_sec *1000 + chart_time_mic /1000
                    #print "chart_time:%s,%s,%s,%s" % (str(chart_time),cus.customername,src_dev,dst_dev)  
                    log_data.info("chart_time:%s,%s,%s,%s" % (str(chart_time),cus.customername,src_dev,dst_dev)) 
        if len(cus.sourcelist)!= 0:
            src_lst = cus.levellist[level_depth-1].devicelist
            dst_lst = cus.sourcelist
            for src_dev in src_lst:
                for dst_dev in dst_lst:
                    monitor_data = gen_dev_chart(cus.customername,src_dev,dst_dev,cus.levellist[level_depth-1].detecttemplate_lst)
                    #print (cus.customername,src_dev,dst_dev,cus.levellist[level_depth-1].detecttemplate_lst,monitor_data)
                    log_data.info("customer_name:%s,%s,%s,%s,%s" % (cus.customername,src_dev,dst_dev,cus.levellist[level_depth-1].detecttemplate_lst,str(monitor_data)))
                    name = cus.customername + '_' + src_dev + '_' + dst_dev + '.png'
                    gen_chart_with_data(cus.customername,src_dev,dst_dev,name,monitor_data)

def CleanDir( Dir ):
    '''
    删除整个目录
    '''
    print "9999999"
    if os.path.isdir( Dir ):
        paths = os.listdir( Dir )
        for path in paths:
            filePath = os.path.join( Dir, path )
            if os.path.isfile( filePath ):
                try:
                    os.remove( filePath )
                    print "6666666"
                except Exception,e:
                    log_message.error( "remove %s error." % filePath )
            elif os.path.isdir( filePath ):
                shutil.rmtree(filePath,True)
    return True


if __name__ == '__main__':

    try:
        opts,args = getopt.getopt(sys.argv[1:],"vdq")
    except getopt.GetoptError:
        print "illegal option(s) -- " + str(sys.argv[1:])

    for name,value in opts:
        if (name == "-v"):
            log_message.info("打印版本:%s" % str(VERSION))
            sys.exit(0)
        if (name == "-d"):
            DEBUG = 1
        if (name == "-q"):
            QUIET = 1

    
    python_daemon()

    try:
        cf=DetectConfigParser(['/root/TTA_detect/config/detector.cfg'])
        cf.do_parse()
        customer_list = cf.customer_list
    except ConfigException,e:
        log_message.error("error in parse config file %s" % str(e))
    try:
        dbconn = MySQLdb.connect(user = 'root',db = 'device_detect_database',passwd = '',charset="utf8")
    except Exception,e:
        log_message.error("Error in connect database:%s" % str(e))
        pass


    while True:
        try:
            gen_all_chart(customer_list)

            path = "/root/"
            #path ="/root/app/detect/app/static/"
            new_path = "/root/picture"
            #new_path = "/root/app/detect/app/static/picture"


            isExists = os.path.exists(new_path)
            if isExists:
                shutil.move("root/picture","/home/") 

            shutil.move("/tmp/picture",path)
            #shutil.move("/root/app/detect/app/picture",path)


            new_isExists = os.path.exists("/home/picture")
            if new_isExists:
                os.system("rm -rf /home/picture")

            time.sleep(DEFAULT_TINE)
        except Exception,e:
            log_message.error("exception:%s occur in loop" % str(e))






    




