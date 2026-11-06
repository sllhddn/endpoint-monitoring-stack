.PHONY: targets up demo down test reload

targets:   ## regenerate Prometheus targets from targets.csv
	python3 scripts/generate_targets.py

up: targets   ## start the monitoring stack only (point targets.csv at real apps)
	docker compose up -d

demo: targets   ## start the stack plus mock application servers
	docker compose --profile demo up -d --build

down:
	docker compose --profile demo down

reload:   ## hot-reload Prometheus after editing rules
	curl -X POST http://localhost:9090/-/reload

test:
	python3 -m pytest -q
