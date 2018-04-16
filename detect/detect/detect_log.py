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

log_path = "/data/proclog/log/detect/"
log_file_message = "/data/proclog/log/detect/detect.log"
log_file_data =    "/data/proclog/log/detect/data.log"

log_http_path = "/data/proclog/log/http_log/"
log_file_http_data = "/data/proclog/log/http_log/http_data.log"
log_file_http_message = "/data/proclog/log/http_log/http_message.log"

try:
    if(not exists(log_path)):
        cmd = str("mkdir -p %s" % log_path);
        system(cmd);

    if(not exists(log_http_path)):
        cmd = str("mkdir -p %s" % log_http_path);
        system(cmd);
    
    Rthandler_message = RotatingFileHandler(log_file_message, maxBytes=100*1024*1024, backupCount=50)
    Rthandler_data = RotatingFileHandler(log_file_data, maxBytes=100*1024*1024, backupCount=50)
    Rthandler_http_data = RotatingFileHandler(log_file_http_data, maxBytes=100*1024*1024, backupCount=50)
    Rthandler_http_message = RotatingFileHandler(log_file_http_message, maxBytes=100*1024*1024, backupCount=50)

    formatter = logging.Formatter('%(asctime)s  %(levelname)8s  %(message)s')
    Rthandler_message.setFormatter(formatter)
    Rthandler_data.setFormatter(formatter)
    Rthandler_http_message.setFormatter(formatter)
    Rthandler_http_data.setFormatter(formatter)
    
    log_message = logging.getLogger("message")
    log_message.addHandler(Rthandler_message)
    log_message.setLevel(logging.DEBUG)
    
    log_data = logging.getLogger("data")
    log_data.addHandler(Rthandler_data)
    log_data.setLevel(logging.DEBUG)

    log_http_data = logging.getLogger("http_data")
    log_http_data.addHandler(Rthandler_http_data)
    log_http_data.setLevel(logging.DEBUG)

    log_http_message = logging.getLogger("http_message")
    log_http_message.addHandler(Rthandler_http_message)
    log_http_message.setLevel(logging.DEBUG)

except:
    pass
