#!/usr/bin/python2.7
import os
import json
import sys
from create_vm import *
import csv
import psutil
import argparse

#This is a web page that is used to create a virtual machine based on limited input.  The code here is really shitty, so apolgies. I might spend a weekend and refactor and use a real OOP model (5/22/2015.). Two months later 2am  7/22 fml.

sessions = {}
class Fields:
    def __init__(self):
        self.all_fields = {}
        self.sdk = None
        self.dry_run = False
        self.iso_only = False
        self.name = "Top"
        #TODO Make this into a damn dict!
        self.field_props = [
            Dropdown("Datacenter", self, ret.datacenters, 
                validator=ret.datacenters),
            Dropdown("Environment", self, ret.environments, 
                validator=ret.environments),
            Text("Hostname", self, validator=val.is_host_avail),
            Text("Subnet", self, validator=val.is_valid_subnet),
            Text("Netmask", self, ret.netmask, validator=ret.netmask),
            Dropdown("IP_Address", self, ret.free_ipplan_ip,
                validator=val.is_dns_available, use_parent_valid=False),
            Text("Gateway", self, validator=val.is_valid_ip),
            Dropdown("Centrify_Zone", self, ret.cent_zones),
            Dropdown("ISO_Version", self, ret.isos),
            Dropdown("Portgroup", self, vco.obj_by_caller,
                validator=vco.obj_by_caller),
            Dropdown("Datastore_1", self, vco.obj_by_caller, 
                validator=vco.obj_by_caller), 
            Dropdown("Datastore_2", self, vco.obj_by_caller, 
                validator=vco.obj_by_caller), 
            Dropdown("Guest_OS", self, vco.obj_by_caller, 
                validator=vco.obj_by_caller), 
            Dropdown("VM_Folder", self, vco.obj_by_caller, 
                validator=vco.obj_by_caller),
            Dropdown("Resource_Pool", self, vco.obj_by_caller, 
                validator=vco.obj_by_caller),
            Dropdown("Cluster", self, vco.obj_by_caller, 
                validator=vco.obj_by_caller),
            Dropdown("Host_System", self, vco.obj_by_caller, 
                validator=vco.obj_by_caller),
            Text("CPU_Count", self, validator=val.has_len),
            Text("Description", self, validator=val.has_len),
            Text("Memory", self, validator=val.has_len),
            Text("Disk_Size_1", self, validator=val.has_len),
            Text("Disk_Size_2", self, validator=val.has_len),
            Text("Contact", self, validator=val.has_len),
            Text("Region", self, validator=val.has_len),
            Text("NBU_vADP", self, validator=val.has_len),
            Checkbox("Dry_Run", self, self.set_dry_run)]

        #These are fields that shouldn't be found in a csv.
        self.mod_fields = ["Dry_Run"]

        self.parent = self
        self.parent_child = {
            "Datacenter":{ 
                "children": 
                    ["Portgroup","Host_System","Guest_OS",
                    "Datastore_1","Datastore_2",
                    "VM_Folder","Resource_Pool",
                    "Cluster","Centrify_Zone"],
                "self_mod" : self.set_sdk }, 

            "Subnet":{"children":["IP_Address", "Netmask"]},
            }
 
        self.rendered_form = self.render_form()
        self.render = web.template.render('templates/')
        self.form = self.render.maestro(self.rendered_form)

    def set_dry_run(self, value):
        self.dry_run = value

    def field_by_name(self, name):
        for field in self.field_props:
            if field.name == name:
                return field

    def update_field(self, field, val):
        parent_keys = self.parent_child.keys()
        field.update(val)
        new_forms = {}
        if field.name in parent_keys:
            parent_dict = self.parent_child[field.name]
            if "self_mod" in parent_dict:
                parent_dict["self_mod"](val)

            for child in parent_dict["children"]:
                child_field = self.field_by_name(child)
                new_form = child_field.update(val, field)
                new_forms[child_field.name] = new_form

        return new_forms
                
    def render_form(self):
        all_fields = []
        for field in self.field_props:
            all_fields.append(field.form)

        return form.Form(*all_fields).render()

    def set_sdk(self, new_sdk=None):
        self.sdk = new_sdk
        return self.sdk

    def ajax_update(self, inputs):
        if len(inputs) == 0:
            return
        name = inputs['name']
        val = inputs['val']

        field = self.field_by_name(name)
        field.value = val
        field.update(val, self)
        updated_fields = self.update_field(field, val)

        new_json_forms = []
        for key in updated_fields:
            rendered_field = updated_fields[key].render().strip()
           
            child_field = self.field_by_name(key)
            rendered_child = child_field.form.render()
            reference_id = "%s" % (child_field.id)
            field_json = {'id':reference_id, 'val':rendered_child}
            
            new_json_forms.append(field_json)

        j_dumps = json.dumps(new_json_forms)

        return j_dumps

    def process_submit(self, data):
        results = {}
        is_good = True
        for name in data.keys():
            value = data[name]
 
            if not self.field_validate(name, value):
                print "Bad data: data[name]"
                is_good = False

        if is_good:
            create_iso(data)
            vco.create_vm(data, self.sdk)

        if False in results.values():
            status = False
        else:
            status = True
        return results,is_good

    def process_csv(self, reader):
        missing_headers = []
        for field in self.field_props:
            if field.name not in reader.fieldnames and field.name not in self.mod_fields:
                print "Missing Header: %s " % (field.name)
                missing_headers.append(field.name)
        if missing_headers:
            return missing_headers

        validation_issues = {} 
        build_items = {}
        for line in reader:
            host = line['Hostname']
            validation_issues[host] = []
            build_items[host] = {}
            for field in self.field_props:
                name = field.name.strip()
                if name in self.mod_fields:
                    continue
                val = line[name].strip()
                field.value = val
                valid = self.field_validate(name, val)
                if not valid:
                    validation_issues[host].append(name)
                if valid and not self.dry_run:
                    build_items[host][name] = val
 
        return build_items,validation_issues

    def field_validate(self, field_name, value, no_parent=False):
        ret = False
        print "Validating %s:%s " % (field_name, value)
        field = self.field_by_name(field_name)

        #Hacky. This will happen for fields such as Dry Run and the csv upload.
        if not field:
            return True

        #Check validation against parent if exists
      
        for par in self.parent_child:
            if field_name in self.parent_child[par]["children"] and not field.use_parent_valid:
                value = self.field_by_name(par).value
                parent = self.field_by_name(par)
                print "Using parent's value %s!" % (value)

        if not field.validator:
            ret = True
        elif value and field.validator:
            val_result = field.validator(value, field)
            print "results %s"  % (val_result)
            if type(val_result) != list:
                val_result = [val_result]

            if field.value and field.value in val_result:
                ret = True
            elif val_result == [True]:
                ret = True

        else:
            print "mother fucker"
        return ret 
        
        
class Checkbox:
    def __init__(self, name, parent, update_func=None, validator=None, use_parent_valid=None):
        self.parent = parent
        self.id = "id_%s" % (name)
        self.name = (name)
        self.value = None
        self.update_func = update_func
        self.form = form.Checkbox(name, id=self.id, class_="ajax-checkbox")
        self.validator = validator
        self.use_parent_valid = use_parent_valid

    def update(self, input_var=None):
        self.value = input_var
        self.update_func(input_var)
  
class Dropdown:
    def __init__(self, name, parent, update_func, list=[], input_var=None, children=None, validator=None, value=None, use_parent_valid=None):
        self.parent = parent
        self.list = list
        self.value = None
        self.id = "id_%s" % (name)
        self.name = (name)
        self.update_func = update_func
        self.validator = validator
        self.use_parent_valid = use_parent_valid

        #initialize the form.Dropdown
        self.form = self.update(input_var)

    def update(self, input_var=None, caller=None):
        func_out = self.update_func(input_var, caller=self)
        prepend_empty = False
      
        if func_out:
            self.list = func_out
            self.list.insert(0,'')

        print "dd name %s value %s" % (self.name, self.value)

        self.form = form.Dropdown(self.name, self.list, id = self.id, class_ = "ajax-dropdown")

        return self.form

class Text:
    def __init__(self, name, parent, update_func=None, value='', input_var=None, children=None, sdk = None, validator=None, regexp='.*', ajax_checker=None, use_parent_valid = None):
        self.parent = parent
        self.update_func = update_func
        self.value = ''
        self.id = "id_%s" % (name)
        self.children = children
        self.name = (name)
        self.validator = validator
        self.ajax_checker = ajax_checker
        self.regexp = regexp
        self.form = self.update(input_var)
        self.use_parent_valid = use_parent_valid

    def update(self, input_var=None, caller=None):
        if self.update_func and input_var:
            self.value = self.update_func(input_var)

        print "t %s %s" % (self.value, input_var)

        self.form = form.Textbox(
                 self.name, 
                 value=self.value,
                 id=self.id, 
                 class_ = "ajax-textfield")

        return self.form

    def ajax_update(self, value):
        new_form = self.update(value)
        if ajax_checker(value):
            self.update_children(self)

        return new_form

class index:            
    def create_session(self):
        sessions[session.session_id] = Fields()
        return sessions[session.session_id].form

    def get_updates(self, input):
        new_updates = sessions[session.session_id].ajax_update(input)
        return str(new_updates)
            
    def GET(self): 
        get_data = web.input()

        keys = get_data.keys()
        if len(get_data) == 2 and 'name' in keys and 'val' in keys:
            web.header('Content-Type', 'application/json')
            json_forms = self.get_updates(get_data)
            return json_forms
        else:
            return self.create_session()

    def POST(self): 
        keep_session = True
        post_data = web.input(csvfile={})
        top_level = sessions[session.session_id]

        csvfile = None
        #This shit needs to move out of POST :|
        if 'csvfile' in post_data:
            print "csvfile!"
            csvfile = post_data['csvfile'].file 
            csvfilename = post_data['csvfile'].filename
            if csvfilename:
                print "Found %s - continuing in CSV mode." % (csvfilename)
                reader = csv.DictReader(csvfile, delimiter=',',quotechar='"')
                csv_builds,problems = top_level.process_csv(reader)
                for host in csv_builds:
                    data = csv_builds[host]
 
                    if problems[host]:
                        print "%s problems! %s" % (host, problems[host])

                    else:
                        create_iso(data) 
                        vco.create_vm(data, data['Datacenter'])

                return problems
            else:
                print "No csv file present. Continuing"
                reader = None

        ret,status = top_level.process_submit(post_data)

        return ret

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Starts and stops Maestro webservice.')
    parser.add_argument('--start', action='store_true', default=False, help='Starts Maestro')
    parser.add_argument('--stop', action='store_true', default=False, help='Stops Maestro')

    args = parser.parse_args()
    del sys.argv[1:] #Because argv[1] is used as the port by webpy. (whyyy)

    if not args.start ^ args.stop: #xor
        parser.print_help()
        sys.exit(1)

    if not os.path.isfile('/opt/maestro/pidfile'):
        if args.stop:
            print "Process already down!"

    else:
        file = open('/opt/maestro/pidfile','r')
        old_pid = int(file.read())

        try:
            proc = psutil.Process(old_pid)
        except:
            proc = None

        if proc:
            fds = proc.open_files()
            if filter(lambda x: x.path == '/opt/maestro/pidfile', fds):
                if args.stop:
                    print "Killing process. %s" % (old_pid)
                    os.kill(old_pid, 9)

                elif args.start:
                    print "Maestro already up!"
                sys.exit(1)
        else:
           if args.stop:
               print "Process already down."
               sys.exit(1)

    print "Running as daemon.. Check /opt/maestro/maestro.log for logs"
    if os.fork():
        sys.exit()

    sys.stdout = open('/opt/maestro/maestro.log','w',0)
    sys.stderr = sys.stdout

    pid_file = open('/opt/maestro/pidfile','w+',0)
    pid_file.write(str(os.getpid()))

    import web
    from web import form
    import lib.validators as val
    import lib.retrievers as ret
    import lib.vcomc as vcomc

    vco = vcomc.Vcoer()

    urls = ('/', 'index' )
    app = web.application(urls, locals())

    session = web.session.Session(app, web.session.DiskStore('sessions'))

    i = index()

    web.internalerror = web.debugerror
    app.run()
