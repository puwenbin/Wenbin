#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日志
"""
import os
import sys
import time
import shutil
import logging
import datetime
import threading
import traceback
from detect_log import *




__all__ = ['loginf', 'logwarn', 'logerr', 'logfatal', 'dbg', 'trace_err',
           'jsonformat']
LOG_PATH = 'log'

def get_logpath():
    try:
        basedir = '/data/proclog/'
        path = __file__.split('/')
        idx = path.index('utils') - 1
        return basedir + path[idx]
    except:
        return 'log'


def log_handle(log_type):
    '''
    获取logging handle

    @params log_type: 日志类型，字符串类型，可选项：'info', 'error'。
    '''
    global LOG_PATH
    logpath = LOG_PATH
    if not os.path.isdir(logpath):
        os.system('rm -rf %s' % logpath)
        os.makedirs(logpath, 0775)
    log_name, path, level, template = {
        #'info': (
        #    'INF', logpath + '/out', logging.INFO,
        #    '%(asctime)s %(levelname)7s %(module)20s.%(funcName)s : %(message)40s'
        #),
        'info': (
            'INF', logpath + '/out', logging.INFO,
            '%(asctime)s %(levelname)7s : %(message)s'
        ),
        'debug': (
            'DBG', logpath + '/debug', logging.DEBUG,
            '%(asctime)s %(levelname)7s %(module)s.%(funcName)s : %(message)s'
        ),
        'error': (
            'ERR', logpath + '/err', logging.WARNING,
            '%(asctime)s %(levelname)8s by %(module)s.%(funcName)s in line %(lineno)d [%(threadName)s] -> %(message)s'
        )
    }[log_type]

    _log = logging.getLogger(log_name)
    hdlr = logging.FileHandler(path)
    formatter = logging.Formatter(template)
    hdlr.setFormatter(formatter)
    _log.addHandler(hdlr)
    _log.setLevel(level)
    return _log


LOG_PATH = get_logpath()
_inf_hdlr = log_handle('info')
_err_hdlr = log_handle('error')
_dbg_hdlr = log_handle('debug')

####
# for debug  in  test 
_inf_hdlr.addHandler(_dbg_hdlr)    
####

debug = _dbg_hdlr.debug
loginf = _inf_hdlr.info
logwarn = _err_hdlr.warning  # 警告
logerr = _err_hdlr.error     # 错误
logfatal = _err_hdlr.fatal   # 致命错误


def open_debug():
    """ 设置debug模式"""
    global _dbg_hdlr
    global _inf_hdlr
    _dbg_hdlr.setLevel(logging.DEBUG)
    _inf_hdlr.addHandler(_dbg_hdlr)    
    loginf("打开调试功能")

def close_debug():
    """ 关闭debug模式"""
    global _dbg_hdlr
    global _inf_hdlr
    _dbg_hdlr.setLevel(logging.ERROR)
    loginf("关闭调试功能")

def trace_code(start_layer=1, max_layers=10):
    module = lambda filename: os.path.splitext(os.path.basename(filename))[0]
    try:
        s = ''
        for i in xrange(start_layer, max_layers + start_layer):
            fcode = sys._getframe(i).f_code
            if fcode.co_name == 'run':
                if sys._getframe(i + 1).f_code.co_name == '__bootstrap_inner':
                    mod = 'Thread_Call: ' + module(fcode.co_filename)
                    s = mod + '.' + fcode.co_name + '.' + s
                    return
            elif fcode.co_name == '_dispatch':
                if sys._getframe(i + 1).f_code.co_name == '_marshaled_dispatch':
                    mod = 'RPC_Call: ' + module(fcode.co_filename)
                    s = mod + '.' + fcode.co_name + '.' + s
                    return
            elif fcode.co_name == '<module>':
                mod = module(fcode.co_filename)
                s = mod + '.' + s
                return
            else:
                s = fcode.co_name + '.' + s
    finally:
        if s and s[-1] == '.':
            s = s[:-1]
        return s


def trace_code(start_layer=1, max_layers=10):
    module = lambda filename: os.path.splitext(os.path.basename(filename))[0]
    try:
        s = ''
        for i in xrange(start_layer, max_layers + start_layer):
            fcode = sys._getframe(i).f_code
            if fcode.co_name == 'run':
                if sys._getframe(i + 1).f_code.co_name == '__bootstrap_inner':
                    mod = 'Thread_Call: ' + module(fcode.co_filename)
                    s = mod + '.' + fcode.co_name + '.' + s
                    return
            elif fcode.co_name == '_dispatch':
                if sys._getframe(i + 1).f_code.co_name == '_marshaled_dispatch':
                    mod = 'RPC_Call: ' + module(fcode.co_filename)
                    s = mod + '.' + fcode.co_name + '.' + s
                    return
            elif fcode.co_name == '<module>':
                mod = module(fcode.co_filename)
                s = mod + '.' + s
                return
            else:
                s = fcode.co_name + '.' + s
    finally:
        if s and s[-1] == '.':
            s = s[:-1]
        return s


def dbg(*args, **kwargs):
    '''
    打印调试数据

    用法：
        a, b, c = 1, 'a string', {'q': [111, 222, 333], 'w': 'poiuy', 'e': 123}
        dbg(b)
        dbg(a, b, c)
        dbg(a, b=b, arg3=jsonformat(c))
    '''
    s = trace_code(2, 1)

    if len(args) == 1 and not kwargs:
        s += ' : ' + str(args[0])
    else:
        for arg in args:
            s += ('\n >>> ' + str(arg))
        for k, v in kwargs.iteritems():
            s += ('\n >>> ' + str(k) + ': ' + str(v))
        s += '\n'
    debug(s)

    # 手动控制，单步执行
    if kwargs.get('block') and raw_input('press e to exit, else continue -> ').lower() == 'e':
        exit()


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


def jsonformat(data):
    '''返回json格式化的数据'''
    if isinstance(data, dict):
        output = '{\n'
        for k, v in data.iteritems():
            output += "    '%s': %s,\n" % (k, v)
        output += '}'
    elif isinstance(data, (list, tuple)):
        output = '[\n'
        for v in data:
            output += "    %s,\n" % v
        output += ']'
    else:
        output = str(data)
    return output




if __name__ == '__main__':
    # test
    debug('debug')
    loginf('loginf')
    logwarn('logwarn')
    logerr('logerr')
    logfatal('logfatal')

    a, b, c = 1, 'a string', {'q': [111, 222, 333], 'w': 'poiuy', 'e': 12345}
    dbg(b)
    dbg(a, b, c)
    dbg(a, b=b, arg3=jsonformat(c))

    try:
        raise
    except:
        trace_err("this is a test")

    log_cutter = LogCutThread()
    log_cutter.setDaemon(True)
    log_cutter.start()
    while 1:
        pass
