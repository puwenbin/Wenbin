import  ConfigParser



class ConfigException(Exception):
    def __init__ (self,msg):
        print msg
        self.expmsg=msg

class DetectTemplate():
    def __init__ (self,templatename,templatetype):
        self.templatename=templatename
        self.templatetype=templatetype

class Devicelist():
    def __init__ (self,level,detectenable,detecttemplate_lst):
        self.level=level
        self.detectenable=detectenable
        self.devicelist=[]
        self.detecttemplate_lst=detecttemplate_lst
        

class Customer():
    def __init__ (self,name):
        self.customername=name
        self.level_depth=0
        self.levellist=[]
        self.sourcelist=[]
        


class DetectConfigParser():
    
    def do_parse_customer_list(self):
         cf_customer_list=[]
         if self.cf.has_option('customer','customer'):
            cf_customer_list = self.cf.get("customer","customer").split(',')
            cf_customer_list= map(lambda x:x.strip(),cf_customer_list)
         return cf_customer_list
         
    def do_parse_devicelist_template_list(self,customer,level):
        detect_template_lst=[]
        template_name_lst=[]
        detail_name='customer' + '_' + customer.customername+'_level_'+ str(level) + '_device'
        
        
        if self.cf.has_option(detail_name,'detect_template'):
            template_name_lst=self.cf.get(detail_name,"detect_template").split(',')
            template_name_lst=map(lambda x:x.strip(),template_name_lst)
                
            for template_name in template_name_lst:
                parse_template_name='detect_template_' + template_name
                if self.cf.has_option(parse_template_name,"type"):
                    template_type=self.cf.get(parse_template_name,"type")
                    detect_template=DetectTemplate(template_name,template_type)
                    detect_template_lst.append(detect_template)

        return detect_template_lst
         
    def do_parse_level_info(self,customer,detectenable,detecttemplate_lst):
        parse_name='customer' + '_' + customer.customername

        for level in range(customer.level_depth):
            level_name = 'level_' + str(level) + '_' + 'devicelist'
            if self.cf.has_option(parse_name,level_name):
                levellist=self.cf.get(parse_name,level_name)
                levellist=levellist.strip().strip(',')
                levellist=levellist.split(',')
                levellist=map(lambda x:x.strip(),levellist)
                devicelist=Devicelist(level,detectenable,detecttemplate_lst)
                devicelist.devicelist=levellist
                
                detail_name=parse_name+'_level_'+ str(level) + '_device'
                if self.cf.has_option(detail_name,'detect_template'):
                    devicelist.detecttemplate_lst=self.do_parse_devicelist_template_list(customer,level)
                    
                
                if self.cf.has_option(detail_name,'detect_enable'):
                    devicelist.detectenable=int(self.cf.get(detail_name,"detect_enable"))
            
                customer.levellist.append(devicelist)
                
            
            
    
    def do_parse_source(self,customer):
        cf_source_list=[]
        parse_name='customer' + '_' + customer.customername

        if self.cf.has_option(parse_name,'source_devicelist'):
            cf_source_list = self.cf.get(parse_name,"source_devicelist").split(',')
            cf_source_list=map(lambda x:x.strip(),cf_source_list)
        return cf_source_list
                
    
                
    def do_parse_customer_template_list(self,customer):
        detect_template_lst=[]
        template_name_lst=[]
        parse_name='customer' + '_' + customer.customername
        
        if self.cf.has_option(parse_name,'detect_template'):
            template_name_lst=self.cf.get(parse_name,"detect_template").split(',')
            template_name_lst=map(lambda x:x.strip(),template_name_lst)
            for template_name in template_name_lst:
                parse_template_name='detect_template_' + template_name
                if self.cf.has_option(parse_template_name,"type"):
                    template_type=self.cf.get(parse_template_name,"type")
                    detect_template=DetectTemplate(template_name,template_type)
                    detect_template_lst.append(detect_template)
        
        return detect_template_lst
            
        
    
            
         
    def do_parse_customer_info(self,customer):
        parse_name='customer' + '_' + customer.customername
        cus_detecttemplate=[]
        detectenable=1
        
        if self.cf.has_option(parse_name,'level_depth'):
            customer.level_depth = int(self.cf.get(parse_name,'level_depth'))
        
             
        if self.cf.has_option(parse_name,'detect_enable'):
            detectenable=int(self.cf.get(parse_name,"detect_enable"))
        
        if self.cf.has_option(parse_name,'detect_template'):
            detecttemplate=self.cf.get(parse_name,"detect_template")
        
        customer.sourcelist=self.do_parse_source(customer)
        
        cus_detecttemplate=self.do_parse_customer_template_list(customer)
       
        self.do_parse_level_info(customer,detectenable,cus_detecttemplate)
        
    
    def do_parse(self):
        try:
            cf_customer_list = self.do_parse_customer_list()
            
            for cf_cus in cf_customer_list:
                customer = Customer(cf_cus)
                self.do_parse_customer_info(customer)    
                self.customer_list.append(customer)
        except Exception,e:
            raise ConfigException(str(e))
            
    def __init__(self, filename):
        self.cf = None
        self.customer_list = []
        
        try:
            cf = ConfigParser.RawConfigParser()
            flist=cf.read(filename)
            if (len(flist)==0):
                raise ConfigException("can't find config file")
            self.cf=cf
            
        except Exception,e:
            raise ConfigException(str(e))


if __name__ == '__main__':
    try:
        cf=DetectConfigParser(['/tmp/1.cfg'])
        cf.do_parse()
        
        
    except ConfigException,e:
        print e.expmsg
    
    
