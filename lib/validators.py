#!/usr/bin/python2.7

from BeautifulSoup import BeautifulSoup
import urllib2
import os
import re
from dns import resolver
import retrievers as ret
import socket

def is_iso_dir(link_name, caller=None):
    html_page = urllib2.urlopen(link_name)
    soup = BeautifulSoup(html_page)

    all_imgs = soup.findAll('a', attrs={'href': re.compile(".img$")})
    if len(all_imgs) >= 1:
        return True

    else:
        return False

def is_valid_subnet(ip, caller=None):
    if is_valid_ip(ip):
        if ip in ret.subnets():
            return True
        else:
            return False
    else:
        return False

def is_host_avail(host, caller=None):
    if not host:
        return True
    cmd = "ping -c 1 -w2 %s > /dev/null 2>&1" % (host)
    response = os.system(cmd)

    if response == 0:
        return False
    else:
        return True

def is_dns_available(ipaddr, caller=None):
    if is_valid_ip(ipaddr):
        #If gethostbyaddr fails, the host is available.
        try:
            socket.gethostbyaddr(ipaddr)
            return False
        except:
            return True
    else:
        return False

def is_valid_ip(ipaddr, caller=None):
    if not ipaddr:
        return False
    if re.match('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',str(ipaddr).strip()):
        return True
    else:
        return False

def is_cent_zone(zone=None, caller=None):
    zones = ret.get_cent_zones()
   
    if zone and zones and zone in zones:
        return True
    else:
        return False

def does_host_exist(hostname, caller=None):
    r = resolver.Resolver()
    r.timeout = 1
    r.lifetime = 1

    try:
        results = r.query(hostname)
        if results:
            return True
        else:
            return False

    except:
        return False

def is_env(env, caller=None):
    if env in [x.lower() for x in ['PROD','DR','QA','DEV/UAT','POC']]:
        return True
    else:
        return False

def check_post_errors(post_data, caller=None):
    return None

def has_len(input, caller=None):
    if len(input) > 0:
        return True
    else:
        return False
