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

from typing import NoReturn
import unittest

import pod_spec


class TestPodSpec(unittest.TestCase):
    """Pod spec unit tests."""

    def test_make_pod_ports(self) -> NoReturn:
        """Testing make pod ports."""
        port = 9104

        expected_result = [
            {
                "name": "mysqld-exporter",
                "containerPort": port,
                "protocol": "TCP",
            }
        ]

        pod_ports = pod_spec._make_pod_ports(port)

        self.assertListEqual(expected_result, pod_ports)

    def test_make_pod_envconfig(self) -> NoReturn:
        """Teting make pod envconfig."""
        config = {}
        relation_state = {
            "mysql_host": "mysql",
            "mysql_port": "3306",
            "mysql_user": "mano",
            "mysql_password": "manopw",
            "mysql_root_password": "rootpw",
        }

        expected_result = {
            "DATA_SOURCE_NAME": "root:{mysql_root_password}@({mysql_host}:{mysql_port})/".format(
                **relation_state
            )
        }

        pod_envconfig = pod_spec._make_pod_envconfig(config, relation_state)

        self.assertDictEqual(expected_result, pod_envconfig)

    def test_make_pod_ingress_resources_without_site_url(self) -> NoReturn:
        """Testing make pod ingress resources without site_url."""
        config = {
            "site_url": "",
            "cluster_issuer": "",
        }
        app_name = "mysqld-exporter"
        port = 9104

        pod_ingress_resources = pod_spec._make_pod_ingress_resources(
            config, app_name, port
        )

        self.assertIsNone(pod_ingress_resources)

    def test_make_pod_ingress_resources(self) -> NoReturn:
        """Testing make pod ingress resources."""
        config = {
            "site_url": "http://mysqld-exporter",
            "cluster_issuer": "",
            "ingress_whitelist_source_range": "",
        }
        app_name = "mysqld-exporter"
        port = 9104

        expected_result = [
            {
                "name": f"{app_name}-ingress",
                "annotations": {
                    "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                },
                "spec": {
                    "rules": [
                        {
                            "host": app_name,
                            "http": {
                                "paths": [
                                    {
                                        "path": "/",
                                        "backend": {
                                            "serviceName": app_name,
                                            "servicePort": port,
                                        },
                                    }
                                ]
                            },
                        }
                    ]
                },
            }
        ]

        pod_ingress_resources = pod_spec._make_pod_ingress_resources(
            config, app_name, port
        )

        self.assertListEqual(expected_result, pod_ingress_resources)

    def test_make_pod_ingress_resources_with_whitelist_source_range(self) -> NoReturn:
        """Testing make pod ingress resources with whitelist_source_range."""
        config = {
            "site_url": "http://mysqld-exporter",
            "cluster_issuer": "",
            "ingress_whitelist_source_range": "0.0.0.0/0",
        }
        app_name = "mysqld-exporter"
        port = 9104

        expected_result = [
            {
                "name": f"{app_name}-ingress",
                "annotations": {
                    "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                    "nginx.ingress.kubernetes.io/whitelist-source-range": config[
                        "ingress_whitelist_source_range"
                    ],
                },
                "spec": {
                    "rules": [
                        {
                            "host": app_name,
                            "http": {
                                "paths": [
                                    {
                                        "path": "/",
                                        "backend": {
                                            "serviceName": app_name,
                                            "servicePort": port,
                                        },
                                    }
                                ]
                            },
                        }
                    ]
                },
            }
        ]

        pod_ingress_resources = pod_spec._make_pod_ingress_resources(
            config, app_name, port
        )

        self.assertListEqual(expected_result, pod_ingress_resources)

    def test_make_pod_ingress_resources_with_https(self) -> NoReturn:
        """Testing make pod ingress resources with HTTPs."""
        config = {
            "site_url": "https://mysqld-exporter",
            "cluster_issuer": "",
            "ingress_whitelist_source_range": "",
            "tls_secret_name": "",
        }
        app_name = "mysqld-exporter"
        port = 9104

        expected_result = [
            {
                "name": f"{app_name}-ingress",
                "annotations": {},
                "spec": {
                    "rules": [
                        {
                            "host": app_name,
                            "http": {
                                "paths": [
                                    {
                                        "path": "/",
                                        "backend": {
                                            "serviceName": app_name,
                                            "servicePort": port,
                                        },
                                    }
                                ]
                            },
                        }
                    ],
                    "tls": [{"hosts": [app_name]}],
                },
            }
        ]

        pod_ingress_resources = pod_spec._make_pod_ingress_resources(
            config, app_name, port
        )

        self.assertListEqual(expected_result, pod_ingress_resources)

    def test_make_pod_ingress_resources_with_https_tls_secret_name(self) -> NoReturn:
        """Testing make pod ingress resources with HTTPs and TLS secret name."""
        config = {
            "site_url": "https://mysqld-exporter",
            "cluster_issuer": "",
            "ingress_whitelist_source_range": "",
            "tls_secret_name": "secret_name",
        }
        app_name = "mysqld-exporter"
        port = 9104

        expected_result = [
            {
                "name": f"{app_name}-ingress",
                "annotations": {},
                "spec": {
                    "rules": [
                        {
                            "host": app_name,
                            "http": {
                                "paths": [
                                    {
                                        "path": "/",
                                        "backend": {
                                            "serviceName": app_name,
                                            "servicePort": port,
                                        },
                                    }
                                ]
                            },
                        }
                    ],
                    "tls": [
                        {"hosts": [app_name], "secretName": config["tls_secret_name"]}
                    ],
                },
            }
        ]

        pod_ingress_resources = pod_spec._make_pod_ingress_resources(
            config, app_name, port
        )

        self.assertListEqual(expected_result, pod_ingress_resources)

    def test_make_readiness_probe(self) -> NoReturn:
        """Testing make readiness probe."""
        port = 9104

        expected_result = {
            "httpGet": {
                "path": "/api/health",
                "port": port,
            },
            "initialDelaySeconds": 10,
            "periodSeconds": 10,
            "timeoutSeconds": 5,
            "successThreshold": 1,
            "failureThreshold": 3,
        }

        readiness_probe = pod_spec._make_readiness_probe(port)

        self.assertDictEqual(expected_result, readiness_probe)

    def test_make_liveness_probe(self) -> NoReturn:
        """Testing make liveness probe."""
        port = 9104

        expected_result = {
            "httpGet": {
                "path": "/api/health",
                "port": port,
            },
            "initialDelaySeconds": 60,
            "timeoutSeconds": 30,
            "failureThreshold": 10,
        }

        liveness_probe = pod_spec._make_liveness_probe(port)

        self.assertDictEqual(expected_result, liveness_probe)

    def test_make_pod_spec(self) -> NoReturn:
        """Testing make pod spec."""
        image_info = {"upstream-source": "bitnami/mysqld-exporter:latest"}
        config = {
            "site_url": "",
            "cluster_issuer": "",
        }
        relation_state = {
            "mysql_host": "mysql",
            "mysql_port": "3306",
            "mysql_user": "mano",
            "mysql_password": "manopw",
            "mysql_root_password": "rootpw",
        }
        app_name = "mysqld-exporter"
        port = 9104

        expected_result = {
            "version": 3,
            "containers": [
                {
                    "name": app_name,
                    "imageDetails": image_info,
                    "imagePullPolicy": "Always",
                    "ports": [
                        {
                            "name": app_name,
                            "containerPort": port,
                            "protocol": "TCP",
                        }
                    ],
                    "envConfig": {
                        "DATA_SOURCE_NAME": "root:{mysql_root_password}@({mysql_host}:{mysql_port})/".format(
                            **relation_state
                        )
                    },
                    "kubernetes": {
                        "readinessProbe": {
                            "httpGet": {
                                "path": "/api/health",
                                "port": port,
                            },
                            "initialDelaySeconds": 10,
                            "periodSeconds": 10,
                            "timeoutSeconds": 5,
                            "successThreshold": 1,
                            "failureThreshold": 3,
                        },
                        "livenessProbe": {
                            "httpGet": {
                                "path": "/api/health",
                                "port": port,
                            },
                            "initialDelaySeconds": 60,
                            "timeoutSeconds": 30,
                            "failureThreshold": 10,
                        },
                    },
                }
            ],
            "kubernetesResources": {"ingressResources": []},
        }

        spec = pod_spec.make_pod_spec(
            image_info, config, relation_state, app_name, port
        )

        self.assertDictEqual(expected_result, spec)

    def test_make_pod_spec_with_ingress(self) -> NoReturn:
        """Testing make pod spec."""
        image_info = {"upstream-source": "bitnami/mysqld-exporter:latest"}
        config = {
            "site_url": "https://mysqld-exporter",
            "cluster_issuer": "",
            "tls_secret_name": "mysqld-exporter",
            "ingress_whitelist_source_range": "0.0.0.0/0",
        }
        relation_state = {
            "mysql_host": "mysql",
            "mysql_port": "3306",
            "mysql_user": "mano",
            "mysql_password": "manopw",
            "mysql_root_password": "rootpw",
        }
        app_name = "mysqld-exporter"
        port = 9104

        expected_result = {
            "version": 3,
            "containers": [
                {
                    "name": app_name,
                    "imageDetails": image_info,
                    "imagePullPolicy": "Always",
                    "ports": [
                        {
                            "name": app_name,
                            "containerPort": port,
                            "protocol": "TCP",
                        }
                    ],
                    "envConfig": {
                        "DATA_SOURCE_NAME": "root:{mysql_root_password}@({mysql_host}:{mysql_port})/".format(
                            **relation_state
                        )
                    },
                    "kubernetes": {
                        "readinessProbe": {
                            "httpGet": {
                                "path": "/api/health",
                                "port": port,
                            },
                            "initialDelaySeconds": 10,
                            "periodSeconds": 10,
                            "timeoutSeconds": 5,
                            "successThreshold": 1,
                            "failureThreshold": 3,
                        },
                        "livenessProbe": {
                            "httpGet": {
                                "path": "/api/health",
                                "port": port,
                            },
                            "initialDelaySeconds": 60,
                            "timeoutSeconds": 30,
                            "failureThreshold": 10,
                        },
                    },
                }
            ],
            "kubernetesResources": {
                "ingressResources": [
                    {
                        "name": "{}-ingress".format(app_name),
                        "annotations": {
                            "nginx.ingress.kubernetes.io/whitelist-source-range": config.get(
                                "ingress_whitelist_source_range"
                            ),
                        },
                        "spec": {
                            "rules": [
                                {
                                    "host": app_name,
                                    "http": {
                                        "paths": [
                                            {
                                                "path": "/",
                                                "backend": {
                                                    "serviceName": app_name,
                                                    "servicePort": port,
                                                },
                                            }
                                        ]
                                    },
                                }
                            ],
                            "tls": [
                                {
                                    "hosts": [app_name],
                                    "secretName": config.get("tls_secret_name"),
                                }
                            ],
                        },
                    }
                ],
            },
        }

        spec = pod_spec.make_pod_spec(
            image_info, config, relation_state, app_name, port
        )

        self.assertDictEqual(expected_result, spec)

    def test_make_pod_spec_without_image_info(self) -> NoReturn:
        """Testing make pod spec without image_info."""
        image_info = None
        config = {
            "site_url": "",
            "cluster_issuer": "",
        }
        relation_state = {
            "mysql_host": "mysql",
            "mysql_port": 3306,
            "mysql_user": "mano",
            "mysql_password": "manopw",
            "mysql_root_password": "rootpw",
        }
        app_name = "mysqld-exporter"
        port = 9104

        spec = pod_spec.make_pod_spec(
            image_info, config, relation_state, app_name, port
        )

        self.assertIsNone(spec)

    def test_make_pod_spec_without_relation_state(self) -> NoReturn:
        """Testing make pod spec without relation_state."""
        image_info = {"upstream-source": "bitnami/mysqld-exporter:latest"}
        config = {
            "site_url": "",
            "cluster_issuer": "",
        }
        relation_state = {}
        app_name = "mysqld-exporter"
        port = 9104

        with self.assertRaises(ValueError):
            pod_spec.make_pod_spec(image_info, config, relation_state, app_name, port)


if __name__ == "__main__":
    unittest.main()
