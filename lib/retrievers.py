#a!/usr/bin/python2.7
import os
import re
import MySQLdb
import ipaddress
#from validators import *
import validators as val
import urllib2
import time
from jira.client import JIRA
from BeautifulSoup import BeautifulSoup

def create_con():
    con = MySQLdb.connect(host=IPPLANHOST,
                          user=IPPLANUSER,
                          db=IPPLANDB,
                          passwd=IPPLANPASS)
                          
    curs = con.cursor()
    return con,curs

#ipplan = ipplandb.IpplanDb()
IPPLANHOST = 'localhost'
IPPLANUSER = 'admin'
IPPLANDB   = 'db'
IPPLANPASS = 'pass'
curs,con = create_con()

def isos(iso, caller=None):
    isos = []
    html_page = urllib2.urlopen("http://localhost/ks/isolinux/")
    soup = BeautifulSoup(html_page)

    all_links = soup.findAll('a', attrs={'href': re.compile("^[^/].*/$")})
    for link in all_links:
        link_name = link.get('href')

        iso_link = "http://localhost/ks/isolinux/" + link_name
        if val.is_iso_dir(iso_link):
            isos.append(link_name.rstrip('/'))

    return isos

def jira_tickets(caller=None):
    tickets_query = jira.search_issues("issueType=97 and status=1")

    tickets = []
    for i in range(0,len(tickets_query)):
        ticket_id = str(tickets_query[i])
        if re.match("^IS-",ticket_id):
            ticket_desc = tickets_query[i].fields.summary
            tickets.append(ticket_id + " " + ticket_desc)

    return tickets

def ticket_fields(ticket, caller=None):
    issue = jira.issue(ticket)
    ticket_fields = vars(issue.fields).items()
    ret_fields = {}

    jira_fields = {}
    for field in jira.fields():
        id = field['id']
        name = field['name']
        jira_fields[id] = name

    for field in ticket_fields:
        name = str(field[0])
        vals = str(field[1])
        if vals == "None":
            vals = None

        if name in jira_fields:
            ret_fields[jira_fields[name]] = vals
    return ret_fields

def subnets(caller=None):
    subnets_query = "SELECT INET_NTOA(baseaddr) FROM base"
    results = run_query(subnets_query)

    subnets = []
    for i in results:
        subnets.append(i[0])

    return subnets

def netmask(subnet, caller=None):
    subnet_size_query = "SELECT subnetsize FROM base WHERE inet_ntoa(baseaddr) = '{0}'".format(subnet)
    result = run_query(subnet_size_query)
    if not result:
        return None
    size = run_query(subnet_size_query)[0]
    if size:
        netmask = ipaddress.IPv4Address(u'255.255.255.255') - size[0] + 1
    return str(netmask)

def cent_zones(datacenter, caller=None):
    region = region_from_dc(datacenter)
    object = "OU=Zones,OU=UNIX,DC=%s,DC=BLANK,DC=int objectclass=container " % (region)
    query_str = "ldapsearch -b %s -s one dn -h %s.BLANK.int 2>/dev/null | grep dn:" % (object,region)
    print query_str
    ldap_query = ldapquery = os.popen(query_str).read().split('\n')

    zones = []

    for line in ldap_query:
        if line:
            grouped = re.match('dn: CN=([^,]*),.*',line)
            zone = grouped.group(1)
            zones.append(zone)
    return zones

def free_ipplan_ip(subnet, caller=None):
    if not subnet:
        return
    base_addr_query = "SELECT baseindex,subnetsize FROM base WHERE inet_ntoa(baseaddr) = '{0}'".format(subnet)
    base_addr_res = run_query(base_addr_query)
    if not base_addr_res:
        return None

    baseindex,size = run_query(base_addr_query)[0]
    subnet_end = ipaddress.ip_address(unicode(subnet)) + size-1

    used_ips_query = "SELECT inet_ntoa(ipaddr) from ipaddr WHERE baseindex = '{0}'".format(baseindex)
    results = run_query(used_ips_query)

    used_ips = []
    free_ips = []
    for i in results:
      used_ips.append(i[0])

    subnet_iter = ipaddress.ip_address(unicode(subnet)) + 1
    while subnet_iter != subnet_end:
      if str(subnet_iter) not in used_ips:
        free_ips.append(str(subnet_iter))

      subnet_iter+=1

    return free_ips

def environments(input=None, caller=None):
    return ['1','2','3','4']

def datacenters(input=None, caller=None):
    return ["here", "there", "theretoo"]

def region_from_dc(input=None, caller=None):
    regions = {'na':["France","Spain","South pole"], 
               'eu':["Myspace", "Reddit"] }

    for key in regions.keys():
        if input in regions[key]:
            return key

    return
    

def run_query(query):
    con,curs=create_con()
    try:
        executed = curs.execute(str(query))
    except:
        print "Mysql connection died. Retrying."
        con,curs=create_con()
        time.sleep(.5)
    con.close()

    results = curs.fetchall()
    return results
