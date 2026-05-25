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

Port policy:

```text
0.0.0.0:9090 Prometheus LAN access
0.0.0.0:3000 Grafana LAN access
127.0.0.1:9100 node_exporter local-only
```

Deployment outline:

```text
1. copy monitoring/ to /opt/serverguard-monitoring
2. chmod +x bin/write-agent-ro-prom.sh
3. run bin/write-agent-ro-prom.sh once
4. docker compose up -d
5. verify node_exporter exposes agent_ro_* metrics
6. verify Prometheus query agent_ro_state_code
7. open Grafana from LAN
8. install a local refresh timer for bin/write-agent-ro-prom.sh
```

Boundary:

```text
No secrets, no Docker socket, no action endpoints, no fixed server IP dependency.
```
