#!/usr/bin/python2.7

from vmw.vco.client import Client
import sys
import time

class Vcoer:
    def __init__(self, obj_classes=None, sdks=None):
        self.vco_conn = Client() #left blank

        self.obj_classes =  {
           'Guest_OS':'VC:VirtualMachineGuestOsIdentifier',
           'Portgroup':'VC:DistributedVirtualPortgroup',
           'Cluster':'VC:ClusterComputeResource',
           'VM_Folder':'VC:VmFolder',
           'Resource_Pool':'VC:ResourcePool',
          'Datacenter':'VC:Datacenter',
           'Virtual_Machine':'VC:VirtualMachine',
           'Datastore_1':'VC:Datastore',
           'Datastore_2':'VC:Datastore',
           'Host_System':'VC:HostSystem' }

        self.sdks = {
           'here':'https://localhost:443/sdk',
           'there':'https://localhost:443/sdk',
           'overthere':'https://localhost:443/sdk',
           'heretoo':'localhost:443/sdk',
           'andthis':'localhost:443/sdk'}

        self.all_objs = self.all_dc_objs()

    def build_workflow(self):
        workflow = self.vco_conn.getWorkflowsWithName('Linux Server Build Kickstart Simple')
        return workflow

    def region_to_sdk(self, region):
        return self.sdks[region]

    def dc_sdk(self,dc_name):
        dc_list = self.datacenter_list()
        if dc_name in dc_list:
            obj = self.datacenter_list()[dc_name]
            return obj.properties['vimHost']
        else:
            return False

    def obj_by_caller(self, input_var, caller=None):
        print "caller %s inputvar %s" % (caller.name, input_var)
        if caller:
            if caller.name and input_var:
                if caller.name != 'Datacenter':
                    sdk_dc = caller.parent.sdk
                else:
                    sdk_dc = caller.name
                obj_list = self.all_objs[sdk_dc][caller.name]
                return obj_list.keys()

        return 
            
    def datacenter_list(self, value, caller=None):
        ret = []
        raw_list = self.all_sdk_objs_by_type('Datacenter')
        print "raw list %s" % (raw_list)
        for sdk in raw_list:
            keys = sdk.keys()
            for key in keys:
                ret.append(key)
        return ret
             
    def all_sdk_objs_by_type(self,obj_type, caller=None):
        ret = []
        for sdk in self.all_objs:
            if obj_type in self.all_objs[sdk]: 
                for obj in self.all_objs[sdk][obj_type]:
                    itm = {obj:self.all_objs[sdk][obj_type][obj]}
                    ret.append(itm)
        return ret

    def get_sdk_region(self, sdk):
        return self.sdks[sdk].split('.')[1]

    def get_dns_by_sdk(self, sdk):
        region = self.sdks[sdk].split('.')[1]
        if region == 'na':
            dns_server = 'localhost'

        elif region == 'eu':
            dns_server = 'localhost'

        return dns_server
 
    def obj_by_name(self,name,obj_type,sdk):
        if name in self.all_objs[sdk][obj_type]:
            ret = self.all_objs[sdk][obj_type][name]
        else:
            ret = None
        return ret

    def all_dc_objs(self, obj_classes=None, sdks=None):
        if not sdks:
            sdks = self.sdks
        if not obj_classes:
            obj_classes = self.obj_classes
        ret = {}
        for sdk in sdks.keys():
            ret[sdk] = {}
            for obj in obj_classes.keys():
                ret[sdk][obj] = {}

        for obj_canon in obj_classes.keys():
            obj_class = obj_classes[obj_canon]
       
            all_objs = self.vco_conn.find(obj_class)
            for obj in all_objs:
                props = obj.properties
                if 'vimHost' not in props:
                    name = props['name']
                    for sdk in sdks:
                        ret[sdk][obj_canon][name] = obj
                elif props['vimHost'] in sdks.values():
                    name = props['name']
                    for key in self.sdks:
                        if self.sdks[key] == props['vimHost']:
                            sdk = key
                    ret[sdk][obj_canon][name] = obj
 
        return ret

    def build_status(self, run):
      return run.getStatus()

    def obj_from_post(self, data, sdk):
        obj_by_post = {}
        for name in data:
            if name in self.all_objs[sdk]:
                obj_by_post[name] = self.all_objs[sdk][name][data[name]]
        return obj_by_post


    def create_vm(self, data, sdk):
        sdk = sdk
        obj_by_post = self.obj_from_post(data,sdk)

        inputs = {
            'cluster': obj_by_post['Cluster'],
            'vmNbOfCpus': int(data['CPU_Count']),
            'description': str(data['Description']),
            'dvPortgroup': obj_by_post['Portgroup'],
            'vmMemorySize' : int(data['Memory'])*1024,
            'name' : str(data['Hostname']),
            'vmDatastore1' : obj_by_post['Datastore_1'],
            'vmDatastore2' : obj_by_post['Datastore_2'],
            'vmDatastore3' : obj_by_post['Datastore_1'],
            'vmHost' : obj_by_post['Host_System'],
            'vmFolder' : obj_by_post['VM_Folder'],
            'pool' : obj_by_post['Resource_Pool'],
            'datacenter' : obj_by_post['Datacenter'],
            'vmGuestOs' : obj_by_post['Guest_OS'],
            'vmDiskSize1' : int(data['Disk_Size_1']),
            'vmDiskSize2' : int(data['Disk_Size_2']),
            'vmDiskSize3' : int(0),
            'filePath' : str('[isos] ') + str(data['Hostname']) + '.iso',
            'vmContact' : str(data['Contact']),
            'NBU_VADP' : str(data['NBU_vADP']),
            'ipAddress' : str(data['IP_Address']),
            'dnsServerFqdn' : str(self.get_dns_by_sdk(sdk)),
            'zoneNameFqdn' : str("%s.home.com" % (self.get_sdk_region(sdk)))
        }

        print inputs
        wf = self.build_workflow()[0]
        run = wf.execute(inputs)

        #Sleep because VCO occasionally takes a status request as a "Go the the next step" for some reason
        time.sleep(5)
        return run
