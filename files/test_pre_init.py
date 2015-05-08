#!/usr/bin/python

import unittest
import mock
from pre_init import PreInitConfig


class TestPreInitConfig(unittest.TestCase):
    @mock.patch('pre_init.consul')
    @mock.patch('pre_init.PreInitConfig.check_rmq')
    @mock.patch('pre_init.PreInitConfig._node_ip')
    @mock.patch('pre_init.PreInitConfig._getContainerHostname')
    @mock.patch('pre_init.Docker')
    def test_check_rmq(self, mock_docker, mock_hostname, mock_node_ip, mock_check_rmq, mock_consul):
        mock_docker.return_value = object
        mock_consul.return_value = object
        mock_check_rmq.return_value = None
        mock_node_ip.return_value = "10.1.1.3"
        mock_hostname.return_value = "container_hostname"
        init = PreInitConfig()
        init.check_rmq()

    @mock.patch('pre_init.PreInitConfig.__init__')
    @mock.patch('pre_init.PreInitConfig.run_service')
    @mock.patch('pre_init.PreInitConfig._get_slave_options')
    @mock.patch('pre_init.PreInitConfig.wait_master')
    def test_run_slave(self, mock_wait, mock_get_options, mock_run_service, mock_init):
        rmq_slave_options = "-m SERVICE_NAME", "-c 1"
        mock_wait.return_value = True
        mock_get_options.return_value = rmq_slave_options
        mock_init.return_value = None
        init = PreInitConfig()
        init.run_slave()
        self.assertEqual(mock_wait.call_count, 1)
        self.assertEqual(mock_run_service.call_count, 1)
        self.assertEqual(mock_run_service.call_args_list[0][0][0], rmq_slave_options)
        self.assertEqual(mock_get_options.call_count, 1)

    @mock.patch('pre_init.PreInitConfig._getContainerHostname')
    @mock.patch('pre_init.PreInitConfig.__init__')
    @mock.patch('pre_init.PreInitConfig.run_service')
    @mock.patch('pre_init.PreInitConfig._change_master')
    @mock.patch('pre_init.PreInitConfig.wait_master')
    def test_run_slave_as_master(self, mock_wait, mock_change_master, mock_run_service, mock_init, mock_hostname):
        mock_wait.return_value = False
        mock_change_master.return_value = "container_hostname"
        mock_hostname.return_value = "container_hostname"
        mock_init.return_value = None
        init = PreInitConfig()
        init.run_slave()
        self.assertEqual(mock_wait.call_count, 1)
        self.assertEqual(mock_hostname.call_count, 1)
        self.assertEqual(mock_change_master.call_count, 1)
        self.assertEqual(mock_run_service.call_count, 1)
        self.assertEqual(mock_run_service.call_args_list[0][0], ())

    @mock.patch('pre_init.PreInitConfig._getContainerHostname')
    @mock.patch('pre_init.PreInitConfig._change_master')
    @mock.patch('pre_init.PreInitConfig.__init__')
    @mock.patch('pre_init.PreInitConfig.run_service')
    @mock.patch('pre_init.PreInitConfig._get_slave_options')
    @mock.patch('pre_init.PreInitConfig.wait_master')
    def test_run_slave_after_switch_master(self, mock_wait, mock_get_options, mock_run_service, mock_init,
                                           mock_change_master, mock_hostname):
        rmq_slave_options = ['-m', 'SERVICE_NAME', '-c', '1']
        mock_wait.return_value = False
        mock_get_options.return_value = rmq_slave_options
        mock_change_master.return_value = "new_master_service"
        mock_hostname.return_value = "container_hostname"
        mock_init.return_value = None
        init = PreInitConfig()
        init.run_slave()
        self.assertEqual(mock_wait.call_count, 1)
        self.assertEqual(mock_hostname.call_count, 1)
        self.assertEqual(mock_change_master.call_count, 1)
        self.assertEqual(mock_run_service.call_count, 1)
        self.assertEqual(mock_run_service.call_args_list[0][0][0], rmq_slave_options)
        self.assertEqual(mock_get_options.call_count, 1)

    @mock.patch('pre_init.PreInitConfig.__init__')
    @mock.patch('pre_init.PreInitConfig._get_master_service')
    def test_get_slave_options(self, mock_master_service, mock_init):
        expected_result = ['-m', 'SERVICE_NAME', '-c', '1']
        mock_master_service.return_value = "SERVICE_NAME"
        mock_init.return_value = None
        init = PreInitConfig()
        result = init._get_slave_options()
        self.assertEqual(result, expected_result)

    @mock.patch('pre_init.httplib2.Http.request')
    @mock.patch('pre_init.PreInitConfig.get_master_service_ip')
    @mock.patch('pre_init.PreInitConfig._get_master_service')
    @mock.patch('pre_init.consul')
    @mock.patch('pre_init.PreInitConfig.check_rmq')
    @mock.patch('pre_init.PreInitConfig._node_ip')
    @mock.patch('pre_init.PreInitConfig._getContainerHostname')
    @mock.patch('pre_init.Docker')
    def test_change_master_new(self, mock_docker, mock_hostname, mock_node_ip, mock_check_rmq, mock_consul,
                               mock_master_service, mock_master_ip, mock_http):
        mock_master_service.return_value = "old_rabbit"
        mock_docker.return_value = object
        mock_consul.return_value = object
        mock_check_rmq.return_value = None
        mock_node_ip.return_value = "10.1.1.3"
        mock_master_ip.return_value = "10.1.1.1"
        mock_hostname.return_value = "container_hostname"
        init = PreInitConfig()
        services = (555, [
            {
                "Node": "Node1",
                "Address": "10.1.1.1",
                "ServiceID": "rabbit1",
                "ServiceName": "rabbit1",
                "ServiceTags": [],
                "ServiceAddress": "",
                "ServicePort": 15672
            },
            {
                "Node": "Node2",
                "Address": "10.1.1.2",
                "ServiceID": "rabbit2",
                "ServiceName": "rabbit2",
                "ServiceTags": [],
                "ServiceAddress": "",
                "ServicePort": 15672
            },
            {
                "Node": "Node3",
                "Address": "10.1.1.3",
                "ServiceID": "rabbit3",
                "ServiceName": "rabbit3",
                "ServiceTags": [],
                "ServiceAddress": "",
                "ServicePort": 15672
            }
        ])
        expected_result = "new_rabbit"
        init.consul_cluster_client.catalog.service = mock.Mock(return_value=services)
        mock_http.return_value = ("api_header",
                                  '[{"name":"rabbit@old_rabbit","type":"disc","running":false}, {"name":"rabbit@new_rabbit","type":"disc","running":true}]')

        response_cas = (562, {
            "CreateIndex": 100,
            "ModifyIndex": 200,
            "LockIndex": 200,
            "Key": "foo",
            "Flags": 0,
            "Value": "bar",
            "Session": "adf4238a-882b-9ddc-4a9d-5b6758e4159e"
        })
        response_cas_expected = 200
        init.consul_cluster_client.kv.get = mock.Mock(return_value=response_cas)
        init.consul_cluster_client.kv.put = mock.Mock()
        result = init._change_master()

        self.assertEqual(init.consul_cluster_client.catalog.service.call_count, 1)
        self.assertEqual(mock_http.call_count, 1)
        self.assertEqual(mock_master_ip.call_count, 1)
        self.assertEqual(mock_hostname.call_count, 1)

        self.assertEqual(init.consul_cluster_client.kv.get.call_count, 1)
        self.assertEqual(init.consul_cluster_client.kv.put.call_count, 1)
        self.assertEqual(init.consul_cluster_client.kv.put.call_args_list[0][0], ('master_rmq', expected_result,))
        self.assertEqual(init.consul_cluster_client.kv.put.call_args_list[0][1], {'cas': response_cas_expected})
        self.assertEqual(result, expected_result)

    @mock.patch('pre_init.httplib2.Http.request')
    @mock.patch('pre_init.PreInitConfig.get_master_service_ip')
    @mock.patch('pre_init.PreInitConfig._get_master_service')
    @mock.patch('pre_init.consul')
    @mock.patch('pre_init.PreInitConfig.check_rmq')
    @mock.patch('pre_init.PreInitConfig._node_ip')
    @mock.patch('pre_init.PreInitConfig._getContainerHostname')
    @mock.patch('pre_init.Docker')
    def test_change_master_self(self, mock_docker, mock_hostname, mock_node_ip, mock_check_rmq, mock_consul,
                                mock_master_service, mock_master_ip, mock_http):
        mock_master_service.return_value = "old_rabbit"
        mock_docker.return_value = object
        mock_consul.return_value = object
        mock_check_rmq.return_value = None
        mock_node_ip.return_value = "10.1.1.2"
        mock_master_ip.return_value = "10.1.1.1"
        mock_hostname.return_value = "container_hostname"
        init = PreInitConfig()
        services = (555, [
            {
                "Node": "Node1",
                "Address": "10.1.1.1",
                "ServiceID": "rabbit1",
                "ServiceName": "rabbit1",
                "ServiceTags": [],
                "ServiceAddress": "",
                "ServicePort": 15672
            },
            {
                "Node": "Node2",
                "Address": "10.1.1.2",
                "ServiceID": "rabbit2",
                "ServiceName": "rabbit2",
                "ServiceTags": [],
                "ServiceAddress": "",
                "ServicePort": 15672
            }
        ])
        expected_result = "container_hostname"
        init.consul_cluster_client.catalog.service = mock.Mock(return_value=services)
        response_cas = (562, {
            "CreateIndex": 100,
            "ModifyIndex": 200,
            "LockIndex": 200,
            "Key": "foo",
            "Flags": 0,
            "Value": "bar",
            "Session": "adf4238a-882b-9ddc-4a9d-5b6758e4159e"
        })
        response_cas_expected = 200
        init.consul_cluster_client.kv.get = mock.Mock(return_value=response_cas)
        init.consul_cluster_client.kv.put = mock.Mock()
        result = init._change_master()

        self.assertEqual(init.consul_cluster_client.catalog.service.call_count, 1)
        self.assertEqual(mock_http.call_count, 0)
        self.assertEqual(mock_master_ip.call_count, 1)
        self.assertEqual(mock_hostname.call_count, 1)

        self.assertEqual(init.consul_cluster_client.kv.get.call_count, 1)
        self.assertEqual(init.consul_cluster_client.kv.put.call_count, 1)
        self.assertEqual(init.consul_cluster_client.kv.put.call_args_list[0][0], ('master_rmq', expected_result,))
        self.assertEqual(init.consul_cluster_client.kv.put.call_args_list[0][1], {'cas': response_cas_expected})
        self.assertEqual(result, expected_result)

    @mock.patch('pre_init.httplib2.Http.request')
    @mock.patch('pre_init.PreInitConfig.get_master_service_ip')
    @mock.patch('pre_init.PreInitConfig._get_master_service')
    @mock.patch('pre_init.consul')
    @mock.patch('pre_init.PreInitConfig.check_rmq')
    @mock.patch('pre_init.PreInitConfig._node_ip')
    @mock.patch('pre_init.PreInitConfig._getContainerHostname')
    @mock.patch('pre_init.Docker')
    def test_change_master_if_all_stopping(self, mock_docker, mock_hostname, mock_node_ip, mock_check_rmq, mock_consul,
                                           mock_master_service, mock_master_ip, mock_http):
        mock_master_service.return_value = "old_rabbit"
        mock_docker.return_value = object
        mock_consul.return_value = object
        mock_check_rmq.return_value = None
        mock_node_ip.return_value = "10.1.1.3"
        mock_master_ip.return_value = "10.1.1.1"
        mock_hostname.return_value = "container_hostname"
        init = PreInitConfig()
        services = (555, [
            {
                "Node": "Node1",
                "Address": "10.1.1.1",
                "ServiceID": "rabbit1",
                "ServiceName": "rabbit1",
                "ServiceTags": [],
                "ServiceAddress": "",
                "ServicePort": 15672
            },
            {
                "Node": "Node2",
                "Address": "10.1.1.2",
                "ServiceID": "rabbit2",
                "ServiceName": "rabbit2",
                "ServiceTags": [],
                "ServiceAddress": "",
                "ServicePort": 15672
            },
            {
                "Node": "Node3",
                "Address": "10.1.1.3",
                "ServiceID": "rabbit3",
                "ServiceName": "rabbit3",
                "ServiceTags": [],
                "ServiceAddress": "",
                "ServicePort": 15672
            }
        ])
        expected_result = "container_hostname"
        init.consul_cluster_client.catalog.service = mock.Mock(return_value=services)
        mock_http.return_value = ("api_header",
                                  '[{"name":"rabbit@old_rabbit","type":"disc","running":false}, {"name":"rabbit@new_rabbit","type":"disc","running":false}]')
        response_cas = (562, {
            "CreateIndex": 100,
            "ModifyIndex": 200,
            "LockIndex": 200,
            "Key": "foo",
            "Flags": 0,
            "Value": "bar",
            "Session": "adf4238a-882b-9ddc-4a9d-5b6758e4159e"
        })
        response_cas_expected = 200
        init.consul_cluster_client.kv.get = mock.Mock(return_value=response_cas)
        init.consul_cluster_client.kv.put = mock.Mock()
        result = init._change_master()

        self.assertEqual(init.consul_cluster_client.catalog.service.call_count, 1)
        self.assertEqual(mock_http.call_count, 1)
        self.assertEqual(mock_master_ip.call_count, 1)
        self.assertEqual(mock_hostname.call_count, 1)

        self.assertEqual(init.consul_cluster_client.kv.get.call_count, 1)
        self.assertEqual(init.consul_cluster_client.kv.put.call_count, 1)
        self.assertEqual(init.consul_cluster_client.kv.put.call_args_list[0][0], ('master_rmq', expected_result,))
        self.assertEqual(init.consul_cluster_client.kv.put.call_args_list[0][1], {'cas': response_cas_expected})
        self.assertEqual(result, expected_result)

    @mock.patch('pre_init.consul.Consul')
    @mock.patch('pre_init.PreInitConfig.check_rmq')
    @mock.patch('pre_init.PreInitConfig._getContainerHostname')
    @mock.patch('pre_init.PreInitConfig.__init__')
    def test_create_service(self, mock_init, mock_hostname, mock_check_rmq, mock_reg):
        mock_init.return_value = None
        mock_check_rmq.return_value = None
        node_ip = "10.1.1.3"
        mock_hostname.return_value = "container_hostname"

        init = PreInitConfig()
        init._node_ip = node_ip
        service_name = init._create_service()
        self.assertEqual(mock_hostname.call_count, 1)
        self.assertEqual(mock_reg.call_count, 1)
        self.assertEqual(service_name, "container_hostname")

    @mock.patch('pre_init.consul')
    @mock.patch('pre_init.PreInitConfig.check_rmq')
    @mock.patch('pre_init.PreInitConfig._node_ip')
    @mock.patch('pre_init.Docker')
    def test_getNodeNameByIP(self, mock_docker, mock_node_ip, mock_check_rmq, mock_consul):
        mock_docker.return_value = object
        mock_consul.return_value = object
        mock_check_rmq.return_value = None
        mock_node_ip.return_value = "10.1.1.3"

        init = PreInitConfig()
        response = (123, [
            {
                "Node": "baz",
                "Address": "10.1.1.1"
            },
            {
                "Node": "foobar",
                "Address": "10.1.1.3"
            }
        ])
        init.consul_cluster_client.catalog.nodes = mock.Mock(return_value=response)
        node_name = init._getNodeNameByIP("10.1.1.3")
        self.assertEqual(node_name, "foobar")

    @mock.patch('pre_init.consul')
    @mock.patch('pre_init.PreInitConfig.check_rmq')
    @mock.patch('pre_init.PreInitConfig._node_ip')
    @mock.patch('pre_init.Docker')
    def test_getNodeNameByIP_None(self, mock_docker, mock_node_ip, mock_check_rmq, mock_consul):
        mock_docker.return_value = object
        mock_consul.return_value = object
        mock_check_rmq.return_value = None
        mock_node_ip.return_value = "10.1.1.3"

        init = PreInitConfig()
        response = (123, [
            {
                "Node": "baz",
                "Address": "10.1.1.1"
            },
            {
                "Node": "foobar",
                "Address": "10.1.1.3"
            }
        ])
        init.consul_cluster_client.catalog.nodes = mock.Mock(return_value=response)
        node_name = init._getNodeNameByIP("10.1.1.2")
        self.assertIsNone(node_name)

    @mock.patch('pre_init.socket.socket.connect_ex')
    @mock.patch('pre_init.time.sleep')
    @mock.patch('pre_init.PreInitConfig._get_master_service')
    @mock.patch('pre_init.consul')
    @mock.patch('pre_init.PreInitConfig.check_rmq')
    @mock.patch('pre_init.PreInitConfig._node_ip')
    @mock.patch('pre_init.Docker')
    def test_wait_master(self, mock_docker, mock_node_ip, mock_check_rmq, mock_consul, mock_m_service, mock_sleep,
                         mock_sock_connect):
        mock_docker.return_value = object
        mock_consul.return_value = object
        mock_check_rmq.return_value = None
        mock_node_ip.return_value = "10.1.1.3"
        mock_m_service.return_value = "rabbit1"

        init = PreInitConfig()
        response = (123, [
            {
                "Node": "foobar",
                "Address": "10.1.1.1",
                "ServiceID": "rabbit1:5672",
                "ServiceName": "rabbit1",
                "ServiceTags": [],
                "ServicePort": 5672
            },
            {
                "Node": "foobar",
                "Address": "10.1.1.2",
                "ServiceID": "rabbit2:4369",
                "ServiceName": "rabbit2",
                "ServiceTags": [],
                "ServicePort": 4369
            }
        ])
        init.consul_cluster_client.catalog.service = mock.Mock(return_value=response)
        mock_sock_connect.return_value = 0
        result = init.wait_master()

        self.assertEqual(init.consul_cluster_client.catalog.service.call_count, 1)
        self.assertEqual(init.consul_cluster_client.catalog.service.call_args_list[0][1], {"service": "rabbit1"})
        self.assertEqual(mock_sock_connect.call_count, 1)
        self.assertEqual(mock_sock_connect.call_args_list[0][0][0], ("10.1.1.1", 5672))

        self.assertTrue(result)

    @mock.patch('pre_init.socket.socket.connect_ex')
    @mock.patch('pre_init.time.sleep')
    @mock.patch('pre_init.PreInitConfig._get_master_service')
    @mock.patch('pre_init.consul')
    @mock.patch('pre_init.PreInitConfig.check_rmq')
    @mock.patch('pre_init.PreInitConfig._node_ip')
    @mock.patch('pre_init.Docker')
    def test_wait_master_unavailable(self, mock_docker, mock_node_ip, mock_check_rmq, mock_consul, mock_m_service,
                                     mock_sleep, mock_sock_connect):
        mock_docker.return_value = object
        mock_consul.return_value = object
        mock_check_rmq.return_value = None
        mock_node_ip.return_value = "10.1.1.3"
        mock_m_service.return_value = "rabbit1"

        init = PreInitConfig()
        response = (123, [
            {
                "Node": "foobar",
                "Address": "10.1.1.1",
                "ServiceID": "rabbit1:5672",
                "ServiceName": "rabbit1",
                "ServiceTags": [],
                "ServicePort": 5672
            },
            {
                "Node": "foobar",
                "Address": "10.1.1.2",
                "ServiceID": "rabbit2:4369",
                "ServiceName": "rabbit2",
                "ServiceTags": [],
                "ServicePort": 4369
            }
        ])
        init.consul_cluster_client.catalog.service = mock.Mock(return_value=response)
        mock_sock_connect.return_value = 111
        result = init.wait_master()

        self.assertEqual(init.consul_cluster_client.catalog.service.call_count, 1)
        self.assertEqual(init.consul_cluster_client.catalog.service.call_args_list[0][1], {"service": "rabbit1"})
        self.assertEqual(mock_sock_connect.call_count, 12)
        self.assertEqual(mock_sock_connect.call_args_list[0][0][0], ("10.1.1.1", 5672))

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()