# endpoint-monitoring-stack: How to use

This guide covers running the demo, pointing the stack at real servers, reading the dashboard and day-to-day
operations.

## 1. Prerequisites

- Docker Engine 24+ with the Compose plugin (`docker compose version` should work).
  On Ubuntu the package is `docker-compose-v2`; on Windows use Docker Desktop or Docker inside WSL2.
- Python 3.10+ (only for regenerating targets).
- Ports 3000 (Grafana) and 9090 (Prometheus) free on the host.

## 2. Run the demo

```bash
git clone https://github.com/sllhddn/endpoint-monitoring-stack.git
cd endpoint-monitoring-stack
make demo          # same as: python3 scripts/generate_targets.py && docker compose --profile demo up -d --build
```

Wait about a minute for the first probes, then open:

| URL | What you see |
|---|---|
| http://localhost:3000 | Grafana. Log in as `admin` / `admin` (or the value of `GRAFANA_ADMIN_PASSWORD`). The overview dashboard is the home page |
| http://localhost:9090/targets | Prometheus target list: every monitoring URL and whether the probe ran |
| http://localhost:9090/alerts | Alert rules and which are pending or firing |

The demo includes healthy, slow, failing, flaky and unreachable services, so every panel has data.

Stop it with `make down`. Add `-v` to `docker compose down` to also delete stored metrics.

## 3. Monitor your own servers

1. **Edit the inventory.** Replace the rows in `targets.csv`:

   ```csv
   env,module,node,hostname,url
   production,portal,portal-1,app01,http://10.0.0.11:8080/portal/monitoring
   production,portal,portal-2,app02,http://10.0.0.12:8080/portal/monitoring
   staging,portal,portal-stg-1,stg01,http://10.0.1.11:8080/portal/monitoring
   ```

   | Column | Used for |
   |---|---|
   | `env` | Dashboard filter and alert text |
   | `module` | Dashboard filter, "whole module down" alert |
   | `node` | Name shown in tables and alerts |
   | `hostname` | Shown next to the node for quick identification |
   | `url` | The page blackbox_exporter requests; must return HTTP 200 when healthy |

2. **Regenerate targets:** `make targets`. The script refuses duplicate URLs, missing fields and non-HTTP URLs.
3. **Set the password.** Put the monitoring login in `blackbox/monitor_password` (one line, no newline needed) and
   change `username` in `blackbox/blackbox.yml`. Keep real credentials out of Git: add the file to `.gitignore`.
4. **Start without the mock servers:** `make up`.

Prometheus re-reads `targets.json` every minute, so later inventory changes need only `make targets`.

## 4. Read the dashboard

| Panel | Question it answers |
|---|---|
| Nodes monitored / UP / DOWN | How many targets, and how many are failing right now |
| Availability (last 1h) | What share of probes succeeded in the last hour |
| Slowest probe now | Is anything close to timing out |
| Node status table | Which node, in which environment, with what HTTP code and response time. Click the URL to open that node's own monitoring page |
| Response time by node | Which node is getting slower over time (early warning) |
| Nodes down over time | When problems started and how long they lasted |

Use the `env` and `module` drop-downs to narrow every panel at once.

## 5. Alerts

| Alert | Fires when | First check |
|---|---|---|
| NodeDown | A probe fails for 2 minutes | Open the node's URL; check the app server and its logs |
| NodeSlow | Successful probes take over 1 s for 5 minutes | CPU, memory, GC pauses, database waits on that node |
| ModuleFullyDown | Every node of one module in one environment is down | Shared dependency: database, load balancer, network |

To send notifications, add Alertmanager to `docker-compose.yml` and an `alerting:` block to `prometheus.yml`, then
configure email or Teams receivers.

## 6. Reading probe failures

| Probe result | Meaning | Next step |
|---|---|---|
| HTTP 200 | Healthy | none |
| HTTP 401 | Monitoring password wrong | Fix `blackbox/monitor_password` |
| HTTP 404 | Wrong path, or the app is not deployed on that node | Check the URL in `targets.csv` |
| HTTP 500 | App reached but failing | Application logs |
| No HTTP code (`000` in curl) | TCP connection never opened | Firewall, routing or DNS, not the app |

Test reachability from the monitoring host itself, because that is where probes run:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -u monitor:PASSWORD http://10.0.0.11:8080/portal/monitoring
```

If `ping` works but `curl` returns `000`, a firewall rule is blocking that port.

## 7. Day-to-day operations

| Task | Command |
|---|---|
| Reload Prometheus after editing rules | `make reload` |
| See container status | `docker compose ps` |
| Follow Prometheus logs | `docker compose logs -f prometheus` |
| Upgrade images | Change the tags in `docker-compose.yml`, then `docker compose up -d` |
| Back up metrics | Copy the `prometheus-data` volume, or keep the default 15-day retention and accept loss |

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Every node DOWN on first start | Probes have not run yet, or blackbox cannot reach the network | Wait 1 minute; then check `/targets` and the curl test above |
| Stat panels show "No data" | Query returned no series | Panels already use `OR vector(0)`; check the `job` label matches `app_monitoring` |
| Container name conflict on `up` | Compose run from a different folder | Run every command from the repository folder |
| Changes to the dashboard JSON not visible | Grafana reloads provisioned files every 30 s | Wait, then refresh the browser |

## 9. Run the tests

```bash
pip install pytest && pytest -q
```

Tests check the target generator and the dashboard JSON. CI also runs `promtool check config` and starts the full
stack to confirm every target is probed.
