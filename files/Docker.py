#!/usr/bin/python

from docker import Client
import syslog
import os
import string


class Docker(object):
    def __init__(self):
        self.docker_url = "unix://var/run/docker.sock"
        self.docker_version = "1.16"
        self.swarm_container = os.environ.get("SWARM_AGENT_NAME", "swarm-agent")

    def get_node_address(self):
        info = {}
        try:
            docker_client = Client(base_url=self.docker_url, version=self.docker_version)
            node_ip_port = docker_client.inspect_container(self.swarm_container).get("Args", [])

            if node_ip_port:
                node_ip, node_port = string.split(node_ip_port[2], ":")
                info["ip"] = str(node_ip)
                info["port"] = str(node_port)
        except Exception as e:
            syslog.syslog(syslog.LOG_ERR, "Docker API: get_node_address Error: " + e.__str__())

        return info