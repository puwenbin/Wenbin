#!/usr/bin/python
''' log module for nps
    max-size:   100 M
    rotate-num: 5
'''

import sys
from os.path import basename
from os.path import exists
from os import system
import logging
from logging.handlers import RotatingFileHandler

log_path = "/data/proclog/log/report/"
log_file_message = "/data/proclog/log/report/report.log"
log_file_data =    "/data/proclog/log/report/data.log"

log_chart_path = "/data/proclog/log/chart/"
log_file_chart_data = "/data/proclog/log/chart/chart_data.log"
log_file_chart_message = "/data/proclog/log/chart/chart_message.log"

try:
    if(not exists(log_path)):
        cmd = str("mkdir -p %s" % log_path);
        system(cmd);

    if(not exists(log_chart_path)):
        cmd = str("mkdir -p %s" % log_chart_path);
        system(cmd);
    
    Rthandler_message = RotatingFileHandler(log_file_message, maxBytes=100*1024*1024, backupCount=50)
    Rthandler_data = RotatingFileHandler(log_file_data, maxBytes=100*1024*1024, backupCount=50)
    Rthandler_chart_data = RotatingFileHandler(log_file_chart_data, maxBytes=100*1024*1024, backupCount=50)
    Rthandler_chart_message = RotatingFileHandler(log_file_chart_message, maxBytes=100*1024*1024, backupCount=50)

    formatter = logging.Formatter('%(asctime)s  %(levelname)8s  %(message)s')
    Rthandler_message.setFormatter(formatter)
    Rthandler_data.setFormatter(formatter)
    Rthandler_chart_message.setFormatter(formatter)
    Rthandler_chart_data.setFormatter(formatter)
    
    log_message = logging.getLogger("message")
    log_message.addHandler(Rthandler_message)
    log_message.setLevel(logging.DEBUG)
    
    log_data = logging.getLogger("data")
    log_data.addHandler(Rthandler_data)
    log_data.setLevel(logging.DEBUG)

    log_chart_data = logging.getLogger("chart_data")
    log_chart_data.addHandler(Rthandler_chart_data)
    log_chart_data.setLevel(logging.DEBUG)

    log_chart_message = logging.getLogger("chart_message")
    log_chart_message.addHandler(Rthandler_chart_message)
    log_chart_message.setLevel(logging.DEBUG)

except:
    pass
