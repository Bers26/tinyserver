# ServerGuard monitoring stack MVP

This pack wires Agent RO Prometheus text output into node_exporter textfile collector, Prometheus and Grafana.

Runtime target:

```text
/opt/serverguard-monitoring
```

Components:

```text
compose.yml
prometheus/prometheus.yml
grafana/provisioning/datasources/prometheus.yml
grafana/provisioning/dashboards/dashboards.yml
grafana/dashboards/serverguard-agent-ro.json
bin/write-agent-ro-prom.sh
textfile/agent_ro.prom
```

Ports bind to localhost only:

```text
127.0.0.1:9090 Prometheus
127.0.0.1:3000 Grafana
127.0.0.1:9100 node_exporter
```

Deployment outline:

```text
1. copy monitoring/ to /opt/serverguard-monitoring
2. chmod +x bin/write-agent-ro-prom.sh
3. run bin/write-agent-ro-prom.sh once
4. docker compose up -d
5. verify node_exporter exposes agent_ro_* metrics
6. verify Prometheus query agent_ro_state_code
7. open Grafana through SSH/local tunnel or localhost access
```

Boundary:

```text
No secrets, no Docker socket, no action endpoints, no public bind by default.
```
