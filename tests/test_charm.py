#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact: legal@canonical.com
#
# To get in touch with the maintainers, please contact:
# osm-charmers@lists.launchpad.net
##

import sys
from typing import NoReturn
import unittest

from charm import MysqlExporterCharm
from ops.model import ActiveStatus, BlockedStatus
from ops.testing import Harness


class TestCharm(unittest.TestCase):
    """Mysql Exporter Charm unit tests."""

    def setUp(self) -> NoReturn:
        """Test setup"""
        self.image_info = sys.modules["oci_image"].OCIImageResource().fetch()
        self.harness = Harness(MysqlExporterCharm)
        self.harness.set_leader(is_leader=True)
        self.harness.begin()
        self.config = {
            "ingress_whitelist_source_range": "",
            "tls_secret_name": "",
            "site_url": "https://mysql-exporter.192.168.100.100.nip.io",
            "cluster_issuer": "vault-issuer",
        }
        self.harness.update_config(self.config)

    def test_config_changed_no_relations(
        self,
    ) -> NoReturn:
        """Test ingress resources without HTTP."""

        self.harness.charm.on.config_changed.emit()

        # Assertions
        self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)
        print(self.harness.charm.unit.status.message)
        self.assertTrue(
            all(
                relation in self.harness.charm.unit.status.message
                for relation in ["mysql"]
            )
        )

    def test_config_changed_non_leader(
        self,
    ) -> NoReturn:
        """Test ingress resources without HTTP."""
        self.harness.set_leader(is_leader=False)
        self.harness.charm.on.config_changed.emit()

        # Assertions
        self.assertIsInstance(self.harness.charm.unit.status, ActiveStatus)

    def test_with_relations(
        self,
    ) -> NoReturn:
        "Test with relations"
        self.initialize_mysql_relation()

        # Verifying status
        self.assertNotIsInstance(self.harness.charm.unit.status, BlockedStatus)

    def test_with_config(
        self,
    ) -> NoReturn:
        "Test with config"
        self.initialize_mysql_relation()

        # Verifying status
        self.assertNotIsInstance(self.harness.charm.unit.status, BlockedStatus)

    def test_mysql_exception_relation_and_config(
        self,
    ) -> NoReturn:
        self.initialize_mysql_config()
        self.initialize_mysql_relation()

        # Verifying status
        self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)

    def initialize_mysql_relation(self):
        mongodb_relation_id = self.harness.add_relation("mysql", "mysql")
        self.harness.add_relation_unit(mongodb_relation_id, "mysql/0")
        self.harness.update_relation_data(
            mongodb_relation_id,
            "mysql/0",
            {
                "user": "user",
                "password": "pass",
                "host": "host",
                "port": "1234",
                "database": "pol",
                "root_password": "root_password",
            },
        )

    def initialize_mysql_config(self):
        self.harness.update_config({"mysql_uri": "mysql://user:pass@mysql-host:3306"})


if __name__ == "__main__":
    unittest.main()


# class TestCharm(unittest.TestCase):
#     """Mysql Exporter Charm unit tests."""
#
#     def setUp(self) -> NoReturn:
#         """Test setup"""
#         self.harness = Harness(MysqldExporterCharm)
#         self.harness.set_leader(is_leader=True)
#         self.harness.begin()
#
#     def test_on_start_without_relations(self) -> NoReturn:
#         """Test installation without any relation."""
#         self.harness.charm.on.start.emit()
#
#         # Verifying status
#         self.assertIsInstance(self.harness.charm.unit.status, BlockedStatus)
#
#         # Verifying status message
#         self.assertGreater(len(self.harness.charm.unit.status.message), 0)
#         self.assertTrue(
#             self.harness.charm.unit.status.message.startswith("Waiting for ")
#         )
#         self.assertIn("mysql", self.harness.charm.unit.status.message)
#         self.assertTrue(self.harness.charm.unit.status.message.endswith(" relation"))
#
#     def test_on_start_with_relations_without_http(self) -> NoReturn:
#         """Test deployment."""
#         expected_result = {
#             "version": 3,
#             "containers": [
#                 {
#                     "name": "mysqld-exporter",
#                     "imageDetails": self.harness.charm.image.fetch(),
#                     "imagePullPolicy": "Always",
#                     "ports": [
#                         {
#                             "name": "mysqld-exporter",
#                             "containerPort": 9104,
#                             "protocol": "TCP",
#                         }
#                     ],
#                     "envConfig": {"DATA_SOURCE_NAME": "root:rootpw@(mysql:3306)/"},
#                     "kubernetes": {
#                         "readinessProbe": {
#                             "httpGet": {
#                                 "path": "/api/health",
#                                 "port": 9104,
#                             },
#                             "initialDelaySeconds": 10,
#                             "periodSeconds": 10,
#                             "timeoutSeconds": 5,
#                             "successThreshold": 1,
#                             "failureThreshold": 3,
#                         },
#                         "livenessProbe": {
#                             "httpGet": {
#                                 "path": "/api/health",
#                                 "port": 9104,
#                             },
#                             "initialDelaySeconds": 60,
#                             "timeoutSeconds": 30,
#                             "failureThreshold": 10,
#                         },
#                     },
#                 },
#             ],
#             "kubernetesResources": {"ingressResources": []},
#         }
#
#         self.harness.charm.on.start.emit()
#
#         # Initializing the mysql relation
#         relation_id = self.harness.add_relation("mysql", "mysql")
#         self.harness.add_relation_unit(relation_id, "mysql/0")
#         self.harness.update_relation_data(
#             relation_id,
#             "mysql/0",
#             {
#                 "host": "mysql",
#                 "port": "3306",
#                 "user": "mano",
#                 "password": "manopw",
#                 "root_password": "rootpw",
#             },
#         )
#
#         # Verifying status
#         self.assertNotIsInstance(self.harness.charm.unit.status, BlockedStatus)
#
#         pod_spec, _ = self.harness.get_pod_spec()
#
#         self.assertDictEqual(expected_result, pod_spec)
#
#     def test_ingress_resources_with_http(self) -> NoReturn:
#         """Test ingress resources with HTTP."""
#         expected_result = {
#             "version": 3,
#             "containers": [
#                 {
#                     "name": "mysqld-exporter",
#                     "imageDetails": self.harness.charm.image.fetch(),
#                     "imagePullPolicy": "Always",
#                     "ports": [
#                         {
#                             "name": "mysqld-exporter",
#                             "containerPort": 9104,
#                             "protocol": "TCP",
#                         }
#                     ],
#                     "envConfig": {"DATA_SOURCE_NAME": "root:rootpw@(mysql:3306)/"},
#                     "kubernetes": {
#                         "readinessProbe": {
#                             "httpGet": {
#                                 "path": "/api/health",
#                                 "port": 9104,
#                             },
#                             "initialDelaySeconds": 10,
#                             "periodSeconds": 10,
#                             "timeoutSeconds": 5,
#                             "successThreshold": 1,
#                             "failureThreshold": 3,
#                         },
#                         "livenessProbe": {
#                             "httpGet": {
#                                 "path": "/api/health",
#                                 "port": 9104,
#                             },
#                             "initialDelaySeconds": 60,
#                             "timeoutSeconds": 30,
#                             "failureThreshold": 10,
#                         },
#                     },
#                 },
#             ],
#             "kubernetesResources": {
#                 "ingressResources": [
#                     {
#                         "name": "mysqld-exporter-ingress",
#                         "annotations": {
#                             "nginx.ingress.kubernetes.io/ssl-redirect": "false",
#                         },
#                         "spec": {
#                             "rules": [
#                                 {
#                                     "host": "mysqld-exporter",
#                                     "http": {
#                                         "paths": [
#                                             {
#                                                 "path": "/",
#                                                 "backend": {
#                                                     "serviceName": "mysqld-exporter",
#                                                     "servicePort": 9104,
#                                                 },
#                                             }
#                                         ]
#                                     },
#                                 }
#                             ]
#                         },
#                     }
#                 ],
#             },
#         }
#
#         self.harness.charm.on.start.emit()
#
#         # Initializing the mysql relation
#         relation_id = self.harness.add_relation("mysql", "mysql")
#         self.harness.add_relation_unit(relation_id, "mysql/0")
#         self.harness.update_relation_data(
#             relation_id,
#             "mysql/0",
#             {
#                 "host": "mysql",
#                 "port": "3306",
#                 "user": "mano",
#                 "password": "manopw",
#                 "root_password": "rootpw",
#             },
#         )
#
#         self.harness.update_config({"site_url": "http://mysqld-exporter"})
#
#         pod_spec, _ = self.harness.get_pod_spec()
#
#         self.assertDictEqual(expected_result, pod_spec)
#
#     def test_ingress_resources_with_https(self) -> NoReturn:
#         """Test ingress resources with HTTPS."""
#         expected_result = {
#             "version": 3,
#             "containers": [
#                 {
#                     "name": "mysqld-exporter",
#                     "imageDetails": self.harness.charm.image.fetch(),
#                     "imagePullPolicy": "Always",
#                     "ports": [
#                         {
#                             "name": "mysqld-exporter",
#                             "containerPort": 9104,
#                             "protocol": "TCP",
#                         }
#                     ],
#                     "envConfig": {"DATA_SOURCE_NAME": "root:rootpw@(mysql:3306)/"},
#                     "kubernetes": {
#                         "readinessProbe": {
#                             "httpGet": {
#                                 "path": "/api/health",
#                                 "port": 9104,
#                             },
#                             "initialDelaySeconds": 10,
#                             "periodSeconds": 10,
#                             "timeoutSeconds": 5,
#                             "successThreshold": 1,
#                             "failureThreshold": 3,
#                         },
#                         "livenessProbe": {
#                             "httpGet": {
#                                 "path": "/api/health",
#                                 "port": 9104,
#                             },
#                             "initialDelaySeconds": 60,
#                             "timeoutSeconds": 30,
#                             "failureThreshold": 10,
#                         },
#                     },
#                 },
#             ],
#             "kubernetesResources": {
#                 "ingressResources": [
#                     {
#                         "name": "mysqld-exporter-ingress",
#                         "annotations": {},
#                         "spec": {
#                             "rules": [
#                                 {
#                                     "host": "mysqld-exporter",
#                                     "http": {
#                                         "paths": [
#                                             {
#                                                 "path": "/",
#                                                 "backend": {
#                                                     "serviceName": "mysqld-exporter",
#                                                     "servicePort": 9104,
#                                                 },
#                                             }
#                                         ]
#                                     },
#                                 }
#                             ],
#                             "tls": [
#                                 {
#                                     "hosts": ["mysqld-exporter"],
#                                     "secretName": "mysqld-exporter",
#                                 }
#                             ],
#                         },
#                     }
#                 ],
#             },
#         }
#
#         self.harness.charm.on.start.emit()
#
#         # Initializing the mysql relation
#         relation_id = self.harness.add_relation("mysql", "mysql")
#         self.harness.add_relation_unit(relation_id, "mysql/0")
#         self.harness.update_relation_data(
#             relation_id,
#             "mysql/0",
#             {
#                 "host": "mysql",
#                 "port": "3306",
#                 "user": "mano",
#                 "password": "manopw",
#                 "root_password": "rootpw",
#             },
#         )
#
#         self.harness.update_config(
#             {
#                 "site_url": "https://mysqld-exporter",
#                 "tls_secret_name": "mysqld-exporter",
#             }
#         )
#
#         pod_spec, _ = self.harness.get_pod_spec()
#
#         self.assertDictEqual(expected_result, pod_spec)
#
#     def test_ingress_resources_with_https_and_ingress_whitelist(self) -> NoReturn:
#         """Test ingress resources with HTTPS and ingress whitelist."""
#         expected_result = {
#             "version": 3,
#             "containers": [
#                 {
#                     "name": "mysqld-exporter",
#                     "imageDetails": self.harness.charm.image.fetch(),
#                     "imagePullPolicy": "Always",
#                     "ports": [
#                         {
#                             "name": "mysqld-exporter",
#                             "containerPort": 9104,
#                             "protocol": "TCP",
#                         }
#                     ],
#                     "envConfig": {"DATA_SOURCE_NAME": "root:rootpw@(mysql:3306)/"},
#                     "kubernetes": {
#                         "readinessProbe": {
#                             "httpGet": {
#                                 "path": "/api/health",
#                                 "port": 9104,
#                             },
#                             "initialDelaySeconds": 10,
#                             "periodSeconds": 10,
#                             "timeoutSeconds": 5,
#                             "successThreshold": 1,
#                             "failureThreshold": 3,
#                         },
#                         "livenessProbe": {
#                             "httpGet": {
#                                 "path": "/api/health",
#                                 "port": 9104,
#                             },
#                             "initialDelaySeconds": 60,
#                             "timeoutSeconds": 30,
#                             "failureThreshold": 10,
#                         },
#                     },
#                 },
#             ],
#             "kubernetesResources": {
#                 "ingressResources": [
#                     {
#                         "name": "mysqld-exporter-ingress",
#                         "annotations": {
#                             "nginx.ingress.kubernetes.io/whitelist-source-range": "0.0.0.0/0",
#                         },
#                         "spec": {
#                             "rules": [
#                                 {
#                                     "host": "mysqld-exporter",
#                                     "http": {
#                                         "paths": [
#                                             {
#                                                 "path": "/",
#                                                 "backend": {
#                                                     "serviceName": "mysqld-exporter",
#                                                     "servicePort": 9104,
#                                                 },
#                                             }
#                                         ]
#                                     },
#                                 }
#                             ],
#                             "tls": [
#                                 {
#                                     "hosts": ["mysqld-exporter"],
#                                     "secretName": "mysqld-exporter",
#                                 }
#                             ],
#                         },
#                     }
#                 ],
#             },
#         }
#
#         self.harness.charm.on.start.emit()
#
#         # Initializing the mysql relation
#         relation_id = self.harness.add_relation("mysql", "mysql")
#         self.harness.add_relation_unit(relation_id, "mysql/0")
#         self.harness.update_relation_data(
#             relation_id,
#             "mysql/0",
#             {
#                 "host": "mysql",
#                 "port": "3306",
#                 "user": "mano",
#                 "password": "manopw",
#                 "root_password": "rootpw",
#             },
#         )
#
#         self.harness.update_config(
#             {
#                 "site_url": "https://mysqld-exporter",
#                 "tls_secret_name": "mysqld-exporter",
#                 "ingress_whitelist_source_range": "0.0.0.0/0",
#             }
#         )
#
#         pod_spec, _ = self.harness.get_pod_spec()
#
#         self.assertDictEqual(expected_result, pod_spec)
#
#     def test_on_mysql_unit_relation_changed(self) -> NoReturn:
#         """Test to see if mysql relation is updated."""
#         self.harness.charm.on.start.emit()
#
#         relation_id = self.harness.add_relation("mysql", "mysql")
#         self.harness.add_relation_unit(relation_id, "mysql/0")
#         self.harness.update_relation_data(
#             relation_id,
#             "mysql/0",
#             {
#                 "host": "mysql",
#                 "port": "3306",
#                 "user": "mano",
#                 "password": "manopw",
#                 "root_password": "rootpw",
#             },
#         )
#
#         # Verifying status
#         self.assertNotIsInstance(self.harness.charm.unit.status, BlockedStatus)
#
#     def test_publish_target_info(self) -> NoReturn:
#         """Test to see if target relation is updated."""
#         expected_result = {
#             "hostname": "mysqld-exporter",
#             "port": "9104",
#             "metrics_path": "/metrics",
#             "scrape_interval": "30s",
#             "scrape_timeout": "15s",
#         }
#
#         self.harness.charm.on.start.emit()
#
#         relation_id = self.harness.add_relation("prometheus-scrape", "prometheus")
#         self.harness.add_relation_unit(relation_id, "prometheus/0")
#         relation_data = self.harness.get_relation_data(relation_id, "mysqld-exporter/0")
#
#         self.assertDictEqual(expected_result, relation_data)
#
#     def test_publish_scrape_info_with_site_url(self) -> NoReturn:
#         """Test to see if target relation is updated."""
#         expected_result = {
#             "hostname": "mysqld-exporter-osm",
#             "port": "80",
#             "metrics_path": "/metrics",
#             "scrape_interval": "30s",
#             "scrape_timeout": "15s",
#         }
#
#         self.harness.charm.on.start.emit()
#
#         self.harness.update_config({"site_url": "http://mysqld-exporter-osm"})
#
#         relation_id = self.harness.add_relation("prometheus-scrape", "prometheus")
#         self.harness.add_relation_unit(relation_id, "prometheus/0")
#         relation_data = self.harness.get_relation_data(relation_id, "mysqld-exporter/0")
#
#         self.assertDictEqual(expected_result, relation_data)
#
#     def test_publish_dashboard_info(self) -> NoReturn:
#         """Test to see if dashboard relation is updated."""
#         self.harness.charm.on.start.emit()
#
#         relation_id = self.harness.add_relation("grafana-dashboard", "grafana")
#         self.harness.add_relation_unit(relation_id, "grafana/0")
#         relation_data = self.harness.get_relation_data(relation_id, "mysqld-exporter/0")
#
#         self.assertTrue("dashboard" in relation_data)
#         self.assertTrue(len(relation_data["dashboard"]) > 0)
#         self.assertEqual(relation_data["name"], "osm-mysql")
#
#
# if __name__ == "__main__":
#     unittest.main()
