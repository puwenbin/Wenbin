#!/usr/bin/env pytbon
# -*- coding: utf-8 -*-

import datetime
import MySQLdb
import os
import Queue
from report_log import *
import threading
import sys
sys.path.append("..")
from detect.get_config import get_global_config,get_customer_name
#from report import trace_err
global_config_dict = get_global_config()
report_addr = global_config_dict["report_addr"]
report_port = global_config_dict["report_port"]
customer_list = get_customer_name()
#print customer_list

def timing1():
    '''
    生成"时间戳"，记录插入数据库的时间
    '''
    td = datetime.datetime.now()
    tm = {}
    tm['d'] = td
    tm['h'] = int(td.strftime("%H"))
    tm['m'] = int(td.strftime("%M"))

    return tm

def create1_database():

    conn = MySQLdb.connect(host = report_addr,user = 'root',passwd = '',charset="utf8")
    
    curs = conn.cursor()
    try:
        return curs.execute('create database da')
    except Exception,e:
        log_message.error("Database da exists:%s" % str(e))
    conn.close()
    curs.close()

def connect_database():
    result = create1_database()
    
    if result == 1:
        conn = MySQLdb.connect(host = report_addr,user = 'root',db = 'data',passwd = '',charset="utf8")
        return conn


class DataSave():
    '''
    探测数据入库线程
    '''
    def __init__(self,host,user,passwd,db_name,charset,params,table_name):
        '''
        出始化
        '''
        self.host = host
        self.user = user
        self.passwd = passwd
        self.charset = charset
        self.db_name = db_name 
        self.params = params
        self.table_name = table_name


    def timing(self):
        '''
        记录数据入库的时间
        '''
        td = datetime.datetime.now()
        tm['d'] = td
        tm['h'] = int(td.strftime("%H"))
        tm['m'] = int(td.strftime("%M"))

        return tm
    def get_conn_old(self):
        '''
        获取连接，在没有创建数据库之前
        '''
        return MySQLdb.connect(host = self.host,user = self.user,passwd = self.passwd,charset = self.charset)

    def get_cursor_old(self,con):
        '''
        在没有创建数据库之前，获取cursor
        '''
        return con.cursor()


    def check_db(self,cur):
        '''
        列出所有数据库
        '''
        db_list = []
        cur.execute("show databases")
        for db in cur.fetchall():
            db_list.append(db[0])
        return db_list


    def create_database(self,cur):
        '''
        创建数据库
        '''
        #co = MySQLdb.connect(host = self.host,user = self.user,passwd = self.passwd,charset = self.charset)
        #cur = co.cursor()
        try:
            #return cur.execute('create database detect_device_database')
            return cur.execute("create database %s" % self.db_name)
            log_message.info("数据库创建成功")
        except Exception,e:
            log_message.error("数据库已经存在:%s" % str(e))

        #con.close()
        #cur.close()

    def get_conn(self):
        '''
        获取连接
        '''
        return MySQLdb.connect(host = self.host,user = self.user,passwd = self.passwd,charset = self.charset,db = self.db_name)

    def get_cursor(self,conn):
        '''
        获取cursor
        '''
        return conn.cursor()

    def close_conn(self,conn):
        '''
        关闭连接
        '''
        if conn != None:
            conn.close()
    def close_cursor(self,curs):
        '''
        关闭cursor
        '''
        if curs != None:
            curs.close()

    def close(self,conn,curs):
        '''
        关闭所有
        '''
        self.close_conn(conn)
        self.close_cursor(curs)
    
    def check_table(self,curs):
        '''
        在当前数据库中获取表的信息
        '''
        tb_list = []
        curs.execute("use %s" % self.db_name)
        curs.execute("select database()")
        #log_message.info("当前所在的数据库:%s" % curs.fetchall()[0])
        all_table = curs.execute("show tables")
        for tb in curs.fetchall():
            tb_list.append(tb[0])
        return tb_list

    def succ_table(self,curs,cr_table):
        '''
        判断表是否创建成功
        '''
        curs.execute("desc %s" % cr_table)
        for i in curs.fetchall():
            log_message.info("表的结构信息:\t%s" %str(i[0]))
        log_message.info("创建表成功")
        return True

    def get_customer_list(self):
        customer_list = []
        customer_list = get_customer_name()
        return customer_list


    def create_table(self,conn,curs,table_name):
        '''
        创建表
        '''
        #customer_list = self.get_customer_list()
        #for i in range(len(customer_list)):
        try:
            sql = '''
            create table %s(
            id INT(11) AUTO_INCREMENT NOT NULL,
            src_device VARCHAR(30) NOT NULL,
            dst_device VARCHAR(30) NOT NULL,
            template_name VARCHAR(60) NOT NULL,
            detect_value TEXT NOT NULL,
            detect_timestmap TEXT NOT NULL,
            first_data_timestamp VARCHAR(60) NOT NULL,
            clock_offsent VARCHAR(30) NOT NULL,
            PRIMARY KEY(id))
            ''' % table_name
            result = curs.execute(sql)
            conn.commit()
            return result
            #self.close(conn,curs)
        except Exception,e:
            log_message.error("创建表失败:%s" % str(e))
    
    def insert_table(self,conn,curs,table_name):
        '''
        向表中插入数据
        '''
        try:
            sql0 = '''
            insert into customer_cok(src_device,dst_device,template_name,detect_value,detect_timestmap,detect_offsent) values(%s,%s,%s,%s,%s,%s,%s)
            '''
            sql = "insert into "+table_name+"(src_device,dst_device,template_name,detect_value,detect_timestmap,first_data_timestamp,clock_offsent) values(%s,%s,%s,%s,%s,%s,%s)"
            print sql
            #params = (('cok','23','http','5678','890','32','21'),('cok','23','45','http','890','5678','45'),('cok','23','ping','56','56','78','34'),('cok','54','ping','34','54','12','12'))
            result = curs.executemany(sql,self.params)
            #result = curs.execute(sql,self.params)
            conn.commit()
            self.close(conn,curs)
            return result
        except Exception,e:
            log_message.error("插入数据失败:%s" % str(e))
            #trace_err()

    def run(self):
        '''
        执行类
        '''
        con = self.get_conn_old()
        cur = self.get_cursor_old(con)
        db_list = self.check_db(cur)
        if self.db_name not in db_list:
            result = self.create_database(cur)
            if result == 1:
                conn = self.get_conn()
                curs = self.get_cursor(conn)
                customer_list = self.get_customer_list()
                result_table = self.create_table(conn,curs,self.table_name)
                if result_table == 0:
                    result_data = self.insert_table(conn,curs,self.table_name)
                    print result_data
        else:
            conn = self.get_conn()
            curs = self.get_cursor(conn)
            customer_list = self.get_customer_list()
            tb_list = self.check_table(curs)
            if self.table_name not in tb_list:
                result_table = self.create_table(conn,curs,self.table_name)
                if result_table == 0:
                    result_data = self.insert_table(conn,curs,self.table_name)
                    print result_data
            else:
                result_data = self.insert_table(conn,curs,self.table_name)
                print result_data
                    

def main():
    global report_addr
    host = report_addr
    user_name = 'root'
    passwd = ''
    charset="utf8"
    db_name = "device_detect_database"
    params_list = [[['23','http','5678','890','32','21','18'],['23','45','http','890','5678','45','89']],[['23','ping','56','56','78','34','89'],['54','ping','34','54','12','12','89']]]
    #params = ('23','http','5678','890','32','21')
    #params = (str(a[i]),str(b[i]),str(c[i]),str(d[i]),str(e[i]),str(g[i]))

    for i in range(len(customer_list)):
        table_name = customer_list[i]
        params = params_list[i]
        data = DataSave(host,user_name,passwd,db_name,charset,params,table_name)
        data.run()


if __name__ == '__main__':
    
    main()




