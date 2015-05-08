#!/usr/bin/python

from Docker import Docker
import consul
import string
import os
import subprocess
import socket
import time
import httplib2
import json


class PreInitConfig(Docker):
    rmq_master_key = os.environ.get("MASTER_KEY_VALUE", "master_rmq")
    service = os.environ.get("RMQ_SERVICE", "rmq")
    retries_delay = 5
    consul_service = os.environ.get("CONSUL_SERVICE_NAME", "consul")  # "consul - 192.168.56.100"

    def __init__(self):
        Docker.__init__(self)
        self.init_script = "/usr/local/sbin/startrmq.sh"
        self.consul_cluster_client = None
        self._node_ip = self._node_ip()
        self.run()

    def run(self):
        self.consul_cluster_client = consul.Consul(self.consul_service)  # consul service name (dns works)
        self.check_rmq()

    def check_rmq(self):
        try:
            service_name = self._create_service()
            kv_master = self.consul_cluster_client.kv.get(self.rmq_master_key)[1]
            if not kv_master:
                result = self.consul_cluster_client.kv.put(self.rmq_master_key, service_name,
                                                           cas=0)  # put master service as a value if it is not available key
                if result is True:
                    self.run_master()
                else:
                    self.run_slave()
            else:
                if kv_master.get("Value", None) == service_name:
                    self.run_master()
                else:
                    self.run_slave()
        except Exception as e:
            syslog.syslog(syslog.LOG_ERR, "RabbitMQ Pre-init:check_rmq Error: " + e.__str__())

    def run_master(self):
        """
        run a master rmq
        runs rabbit without additional options
        """
        self.run_service()

    def run_slave(self):
        """
        run a slave rmq
        joins new rabbit in exist cluster or default start if it in the cluster
        slave RMQ maybe start as a master RMQ if current master RMQ not response (unavailable)
        """
        if self.wait_master():
            self.run_service(self._get_slave_options())
        else:
            master = self._change_master()
            if self._getContainerHostname() == master:
                self.run_service()
            else:
                self.run_service(self._get_slave_options())

    def _get_slave_options(self):
        """
        slave RMQ options
        m - short master node name (it's consul service = container hostname, depends of RMQ clustering options)
        c - clustering
        r - if specified that it's ram cluster node, default disc
        """
        return "-m " + self._get_master_service(), "-c 1"

    def run_service(self, *args):
        """
        runs rmq service (master or slave)
        """
        try:
            subprocess.call([self.init_script] + list(args))
        except Exception as e:
            syslog.syslog(syslog.LOG_ERR, "RabbitMQ Pre-init:run_service Error: " + e.__str__())

    def _change_master(self):
        """
        changes unavailable master RMQ to the new RMQ
        consul KV changes too
        """
        # get rmq nodes
        new_service = self._getContainerHostname()
        services = self.consul_cluster_client.catalog.service(service=self.service)[1]
        current_service_ip = self.get_master_service_ip()
        # create node lists, except current and old master node
        nodes = list(set(node.get("ServiceName") for node in services
                         if node.get("Address") not in (self._node_ip, current_service_ip)))

        if nodes:
            # if we have free rmq nodes, gets one of them
            rmq_node = nodes[0]
            h = httplib2.Http(".cache")
            h.add_credentials('rabbit', 'rabbit')
            (resp_headers, content) = h.request("//{}:15672/api/nodes".format(rmq_node), "GET")

            if content:
                content = json.loads(content)
                cluster_nodes = [item.get("name").split("@")[1] for item in content if
                                 item.get("name", None) and item.get("running", False) is True]
                if len(cluster_nodes):
                    new_service = cluster_nodes[0]

        # update KV by new service name (master rmq)
        cas = self.consul_cluster_client.kv.get(self.rmq_master_key)[1].get("ModifyIndex")
        self.consul_cluster_client.kv.put(self.rmq_master_key, new_service, cas=cas)

        self.forget_cluster_node()

        return new_service

    def get_master_service_ip(self):
        """
        gets current master RMQ ip by consul service name
        """
        current_master = self._get_master_service()
        service_info = self.consul_cluster_client.catalog.service(service=current_master)[1]
        if len(service_info):
            return self.consul_cluster_client.catalog.service(service=current_master)[1][0].get("Address")

    def forget_cluster_node(self):
        """TODO: remove rmq node remotely."""
        pass

    def _create_service(self):
        """
        creates additional consul service by container hostname
        it dns name will be used for rabbitmq clustering
        """
        node_name = self._getNodeNameByIP(self._node_ip)
        container_hostname = self._getContainerHostname()
        if node_name:
            rmq_ports = (5672, 4369, 25672)  # it's standard ports of RMQ
            client = consul.Consul(self._node_ip)
            for port in rmq_ports:
                # register new service
                # TODO: removes when the container is turned off, it needs check health script
                client.agent.service.register(name=node_name,
                                              service_id=":".join((container_hostname, str(port))),
                                              port=int(port))
        return container_hostname

    def _getContainerHostname(self):
        """Retrieves container hostname"""
        return socket.gethostname()

    def _getNodeNameByIP(self, ip):
        """Retrieves current node name by ip, sends request through consul api"""
        nodes = self.consul_cluster_client.catalog.nodes()
        for node in nodes[1]:
            if node.get("Address") == ip:
                name = node.get("Node", None)
                break
        else:
            name = None
        return name

    def _node_ip(self):
        """Gets current node IP through Docker API"""
        #return "192.168.99.102"
        node_info = self.get_node_address()
        return node_info.get("ip")

    def wait_master(self):
        """
        wait master RMQ, 60 sec
        returns True|None
        """
        address = None
        port = None
        master = self._get_master_service()
        services = self.consul_cluster_client.catalog.service(service=master)[1]
        for item in services:
            if "4369" in item.get("ServiceID") and master in item.get("ServiceID"):
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

    def _get_master_service(self):
        """Gets master RMQ service name from consul KV"""
        return self.consul_cluster_client.kv.get(self.rmq_master_key)[1].get("Value", None)


if __name__ == "__main__":
    f = PreInitConfig()