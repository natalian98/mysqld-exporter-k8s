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

# pylint: disable=E0213

from ipaddress import ip_network
import logging
from pathlib import Path
from typing import NoReturn, Optional
from urllib.parse import urlparse

from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardProvider
from charms.prometheus_k8s.v0.prometheus_scrape import MetricsEndpointProvider
from ops.main import main
from opslib.osm.charm import CharmedOsmBase, RelationsMissing
from opslib.osm.interfaces.grafana import GrafanaDashboardTarget
from opslib.osm.interfaces.mysql import MysqlClient
from opslib.osm.interfaces.prometheus import PrometheusScrapeTarget
from opslib.osm.pod import (
    ContainerV3Builder,
    IngressResourceV3Builder,
    PodRestartPolicy,
    PodSpecV3Builder,
)
from opslib.osm.validator import ModelValidator, validator


logger = logging.getLogger(__name__)

PORT = 9104
METRICS_PATH = "/metrics"


class ConfigModel(ModelValidator):
    site_url: Optional[str]
    cluster_issuer: Optional[str]
    ingress_class: Optional[str]
    ingress_whitelist_source_range: Optional[str]
    tls_secret_name: Optional[str]
    mysql_uri: Optional[str]
    image_pull_policy: str
    security_context: bool

    @validator("site_url")
    def validate_site_url(cls, v):
        if v:
            parsed = urlparse(v)
            if not parsed.scheme.startswith("http"):
                raise ValueError("value must start with http")
        return v

    @validator("ingress_whitelist_source_range")
    def validate_ingress_whitelist_source_range(cls, v):
        if v:
            ip_network(v)
        return v

    @validator("mysql_uri")
    def validate_mysql_uri(cls, v):
        if v and not v.startswith("mysql://"):
            raise ValueError("mysql_uri is not properly formed")
        return v

    @validator("image_pull_policy")
    def validate_image_pull_policy(cls, v):
        values = {
            "always": "Always",
            "ifnotpresent": "IfNotPresent",
            "never": "Never",
        }
        v = v.lower()
        if v not in values.keys():
            raise ValueError("value must be always, ifnotpresent or never")
        return values[v]


class MysqlExporterCharm(CharmedOsmBase):
    def __init__(self, *args) -> NoReturn:
        super().__init__(*args, oci_image="image")

        # Provision Kafka relation to exchange information
        self.mysql_client = MysqlClient(self, "mysql")
        self.framework.observe(self.on["mysql"].relation_changed, self.configure_pod)
        self.framework.observe(self.on["mysql"].relation_broken, self.configure_pod)

        # Register relation to provide a Scraping Target
        self.scrape_target = PrometheusScrapeTarget(self, "prometheus-scrape")
        self.framework.observe(
            self.on["prometheus-scrape"].relation_joined, self._publish_scrape_info
        )

        # Register relation to provide a Dasboard Target
        self.dashboard_target = GrafanaDashboardTarget(self, "grafana-dashboard")
        self.framework.observe(
            self.on["grafana-dashboard"].relation_joined, self._publish_dashboard_info
        )

        self.prometheus_provider = MetricsEndpointProvider(
            charm=self,
            relation_name="metrics-endpoint",
            jobs=[
                {
                    "metrics_path": METRICS_PATH,
                    "static_configs": [{"targets": ["*:{}".format(str(PORT))]}],
                }
            ],
        )

        self.dashboard_provider = GrafanaDashboardProvider(
            charm=self,
            relation_name="grafana-dashboards",
        )

    def _publish_scrape_info(self, event) -> NoReturn:
        """Publishes scraping information for Prometheus.

        Args:
            event (EventBase): Prometheus relation event.
        """
        if self.unit.is_leader():
            hostname = (
                urlparse(self.model.config["site_url"]).hostname
                if self.model.config["site_url"]
                else self.model.app.name
            )
            port = str(PORT)
            if self.model.config.get("site_url", "").startswith("https://"):
                port = "443"
            elif self.model.config.get("site_url", "").startswith("http://"):
                port = "80"

            self.scrape_target.publish_info(
                hostname=hostname,
                port=port,
                metrics_path=METRICS_PATH,
                scrape_interval="30s",
                scrape_timeout="15s",
            )

    def _publish_dashboard_info(self, event) -> NoReturn:
        """Publish dashboards for Grafana.

        Args:
            event (EventBase): Grafana relation event.
        """
        if self.unit.is_leader():
            self.dashboard_target.publish_info(
                name="osm-mysql",
                dashboard=Path("templates/mysql_exporter_dashboard.json").read_text(),
            )

    def _check_missing_dependencies(self, config: ConfigModel):
        """Check if there is any relation missing.

        Args:
            config (ConfigModel): object with configuration information.

        Raises:
            RelationsMissing: if kafka is missing.
        """
        missing_relations = []

        if not config.mysql_uri and self.mysql_client.is_missing_data_in_unit():
            missing_relations.append("mysql")

        if missing_relations:
            raise RelationsMissing(missing_relations)

    def build_pod_spec(self, image_info):
        """Build the PodSpec to be used.

        Args:
            image_info (str): container image information.

        Returns:
            Dict: PodSpec information.
        """
        # Validate config
        config = ConfigModel(**dict(self.config))

        if config.mysql_uri and not self.mysql_client.is_missing_data_in_unit():
            raise Exception("Mysql data cannot be provided via config and relation")

        # Check relations
        self._check_missing_dependencies(config)

        data_source = (
            f'{config.mysql_uri.replace("mysql://", "").replace("@", "@(").split("/")[0]})/'
            if config.mysql_uri
            else f"root:{self.mysql_client.root_password}@({self.mysql_client.host}:{self.mysql_client.port})/"
        )

        # Create Builder for the PodSpec
        pod_spec_builder = PodSpecV3Builder(
            enable_security_context=config.security_context
        )

        # Add secrets to the pod
        mysql_secret_name = f"{self.app.name}-mysql-secret"
        pod_spec_builder.add_secret(
            mysql_secret_name,
            {"data_source": data_source},
        )

        # Build container
        container_builder = ContainerV3Builder(
            self.app.name,
            image_info,
            config.image_pull_policy,
            run_as_non_root=config.security_context,
        )
        container_builder.add_port(name="exporter", port=PORT)
        container_builder.add_http_readiness_probe(
            path="/api/health",
            port=PORT,
            initial_delay_seconds=10,
            period_seconds=10,
            timeout_seconds=5,
            success_threshold=1,
            failure_threshold=3,
        )
        container_builder.add_http_liveness_probe(
            path="/api/health",
            port=PORT,
            initial_delay_seconds=60,
            timeout_seconds=30,
            failure_threshold=10,
        )
        container_builder.add_secret_envs(
            mysql_secret_name, {"DATA_SOURCE_NAME": "data_source"}
        )

        container = container_builder.build()

        # Add container to PodSpec
        pod_spec_builder.add_container(container)

        # Add Pod restart policy
        restart_policy = PodRestartPolicy()
        restart_policy.add_secrets(secret_names=(mysql_secret_name))
        pod_spec_builder.set_restart_policy(restart_policy)

        # Add ingress resources to PodSpec if site url exists
        if config.site_url:
            parsed = urlparse(config.site_url)
            annotations = {}
            if config.ingress_class:
                annotations["kubernetes.io/ingress.class"] = config.ingress_class
            ingress_resource_builder = IngressResourceV3Builder(
                f"{self.app.name}-ingress", annotations
            )

            if config.ingress_whitelist_source_range:
                annotations[
                    "nginx.ingress.kubernetes.io/whitelist-source-range"
                ] = config.ingress_whitelist_source_range

            if config.cluster_issuer:
                annotations["cert-manager.io/cluster-issuer"] = config.cluster_issuer

            if parsed.scheme == "https":
                ingress_resource_builder.add_tls(
                    [parsed.hostname], config.tls_secret_name
                )
            else:
                annotations["nginx.ingress.kubernetes.io/ssl-redirect"] = "false"

            ingress_resource_builder.add_rule(parsed.hostname, self.app.name, PORT)
            ingress_resource = ingress_resource_builder.build()
            pod_spec_builder.add_ingress_resource(ingress_resource)

        return pod_spec_builder.build()


if __name__ == "__main__":
    main(MysqlExporterCharm)
