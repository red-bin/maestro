#!/usr/bin/python2.7
import MySQLdb

class IpplanDb:
    def __init__(self):
        self.IPPLANHOST = 'localhost'
        self.IPPLANUSER = 'admin'
        self.IPPLANDB   = 'localdb'
        self.IPPLANPASS = 'pass'

        self.create_con()

    def create_con(self):
        self.con = MySQLdb.connect(host=self.IPPLANHOST,
                              user=self.IPPLANUSER,
                              db=self.IPPLANDB,
                              passwd=self.IPPLANPASS)
                              
        self.curs = self.con.cursor()

    def run_query(self, query):
        print query
        if not query:
            return None
            self.create_con()

        while True:
            try:
                executed = self.curs.execute(str(query))
                self.create_con()
                break
            except:
                print "Mysql connection died. Retrying."
                pass

        results = self.curs.fetchall()
        return results
