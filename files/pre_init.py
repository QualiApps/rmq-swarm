#!/usr/bin/python

from Docker import Docker
import consul
import string
import syslog
import os
import subprocess
import socket
import time


class PreInitConfig(Docker):
    rmq_master_key = "master_rmq"
    service = "rmq"
    primary_tag = "master"
    retries_delay = 5
    consul_service = "consul"

    def __init__(self):
        Docker.__init__(self)
        self.init_script = "/usr/local/sbin/startrmq.sh"
        self.consul_cluster_client = None
        self.run()

    def run(self):
        self.consul_cluster_client = consul.Consul(self.consul_service)  # consul name (dns works)
        self.check_rmq()

    def check_rmq(self):
        try:
            if not self.consul_cluster_client.kv.get(self.rmq_master_key)[1]:
                result = self.consul_cluster_client.kv.put(self.rmq_master_key, self._node_ip(),
                                                           cas=0)  # put master ip if it is not available key
                if result is True:
                    self.run_master()
                else:
                    self.run_slave()
            else:
                self.run_slave()
        except Exception as e:
            print e
            # syslog.syslog(syslog.LOG_ERR, "RabbitMQ Pre-init:check_rmq Error: " + e.__str__())

    def run_master(self):
        """run a master rmq"""
        self.run_service()

    def run_slave(self):
        """run a slave rmq"""
        if self.wait_master():
            master_node = "-m " + self._get_master_ip()
            clustering = "-c"
            self.run_service(master_node, clustering)
        else:
            syslog.syslog(syslog.LOG_ALERT, "RabbitMQ Slave: RMQ Master is not available!")

    def run_service(self, *args):
        try:
            subprocess.call([self.init_script] + list(args))
        except Exception as e:
            syslog.syslog(syslog.LOG_ERR, "RabbitMQ Pre-init:run_service Error: " + e.__str__())

    def _node_ip(self):
        # return "192.168.56.105"
        # return socket.gethostbyname(socket.getfqdn())
        return self.get_node_address()

    def wait_master(self):
        address = None
        port = None
        services = self.consul_cluster_client.catalog.service(service=self.service)[1]
        master_ip = self._get_master_ip()
        for item in services:
            if "4369" in item.get("ServiceID") and master_ip in item.get("Address"):
                address = item.get("Address")
                port = item.get("ServicePort")
                break

        if address and port:
            retries = 0
            while retries < 12:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex((address, port))
                sock.close()
                if not result:
                    return True
                time.sleep(self.retries_delay)
                retries += 1

    def _get_master_ip(self):
        return self.consul_cluster_client.kv.get("master_rmq")[1].get("Value", None)


if __name__ == "__main__":
    f = PreInitConfig()
