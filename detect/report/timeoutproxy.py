# -*- coding: utf-8 -*-
"""
带有超时参数的XML ServerProxy,
示例:
    >>> from pdncommon.timeoutproxy import TimeoutServerProxy
    >>> s = TimeoutServerProxy('http://127.0.0.1:9090',timeout=2)
    >>> print s.echo('hello!')
    hello!
    >>> import socket
    >>> try:
    ...     s.echo("2")
    ... except socket.timeout:
    ...     print "fail"
    ... 
    fail
    >>> 
"""
import xmlrpclib
import httplib


class TimeoutHTTPConnection(httplib.HTTPConnection):
    def connect(self):
        httplib.HTTPConnection.connect(self)
        self.sock.settimeout(self.timeout)


class TimeoutHTTP(httplib.HTTP):
    _connection_class = TimeoutHTTPConnection
    def set_timeout(self, timeout):
        self._conn.timeout = timeout


class TimeoutTransport(xmlrpclib.Transport):
    def __init__(self, timeout=10, *l, **kw):
        xmlrpclib.Transport.__init__(self,*l,**kw)
        self.timeout=timeout
    def make_connection(self, host):
        conn = TimeoutHTTP(host)
        conn.set_timeout(self.timeout)
        return conn


class TimeoutServerProxy(xmlrpclib.ServerProxy):
    def __init__(self,uri,timeout=10,*l,**kw):
        kw['transport']=TimeoutTransport(timeout=timeout, use_datetime=kw.get('use_datetime',0))
        xmlrpclib.ServerProxy.__init__(self,uri,*l,**kw)
