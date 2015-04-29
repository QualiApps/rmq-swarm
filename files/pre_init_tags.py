#!/usr/bin/python

import consul
import string
import syslog
import os
import subprocess
import socket
from pprint import pprint


class PreInitConfig(object):
    service = "db"

    def __init__(self):
        self.init_script = "/usr/local/sbin/startrmq.sh"
        self.primary_tag = "master"
        self.run()

    def run(self):
        self.check_rmq()

    def check_rmq(self):
        # try:
        master_service = {}
        consul_client = consul.Consul("192.168.56.100")

        print consul_client.kv.get("rmq_master")
        print consul_client.kv.put("rmq_master", "ip2", cas=0)
        exit()

        index, items = consul_client.catalog.service(service=self.service)
        if items:
            for item in items:
                tags = item.get("ServiceTags")
                if tags and self.primary_tag in tags:
                    master_service = item
                    break
            else:
                # if it is not master
                service_id = None
                tags = []
                ip = self._node_ip()
                for item in items:
                    address = item.get("Address")
                    if ip in address:
                        service_id = item.get("ServiceID")
                        tags = item.get("ServiceTags") if item.get("ServiceTags") else []
                        break
                if service_id:
                    tags.append(self.primary_tag)
                    self._set_service_tag(service_id, tags)
                    # self.run_service()
            if master_service:
                # run a slave rmq
                # self._wait_rmq()
                node = "-m " + ".".join((self.primary_tag, self.service))
                clustering = "-c"
                self.run_service(node, clustering)
                pass
        else:
            pass
            # except Exception as e:
            # print e
            # syslog.syslog(syslog.LOG_ERR, "RabbitMQ Pre-init:check_rmq Error: " + e.__str__())

    def run_service(self, *args):
        try:
            print [self.init_script] + list(args)
            # subprocess.call([self.init_script] + list(args))
        except Exception as e:
            syslog.syslog(syslog.LOG_ERR, "RabbitMQ Pre-init:run_service Error: " + e.__str__())

    def _set_service_tag(self, service_id, tags):
        consul_current_node = consul.Consul(self._node_ip())
        # consul_current_node.agent.service.deregister("db")
        consul_current_node.agent.service.register(self.service, service_id=service_id, tags=tags)

    @staticmethod
    def _node_ip():
        return socket.gethostbyname(socket.getfqdn())

    def _wait_rmq(self):
        pass


if __name__ == "__main__":
    f = PreInitConfig()