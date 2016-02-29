#!/usr/bin/python
from lib.retrievers import *
import subprocess
import sys

def get_iso_cmd(data):
    hostname = data['Hostname']
    ip = data['IP_Address']
    netmask = data['Netmask']
    gateway = data['Gateway']
    environment = data['Environment']
    zone = data['Centrify_Zone']
    tags = None
    region = data['Region']
    out = "/opt/isos/" + hostname + ".iso"

    opts = "-h %s -i %s -n %s -g %s -e %s -z %s -T -r %s -o %s" % (hostname,ip,netmask,gateway,environment,zone,region,out)
    cmd = "/opt/installmedia/autoiso/mkiso" + " " + opts

    return cmd


def rsync_autoiso():
    rsync_ret = subprocess.call("rsync -ravzq --no-motd cer-lx-unixutil1:/opt/installmedia/autoiso /opt/installmedia 2>/dev/null",shell=True)
     
    if rsync_ret != 0:
        return False
    else:
        subprocess.call("chmod 755 /opt/installmedia/autoiso/isolinux/*",shell=True)
        return True
    

def create_iso(data):
    #ensure dir is synced up with unixutil
    rsync_autoiso()

    command = get_iso_cmd(data)
    ret = subprocess.call(command, shell=True)
    if ret != 0:
        return "ISO Build failed! Investigate!"
    else:
        return "ISO build was successful. Moving on." 

