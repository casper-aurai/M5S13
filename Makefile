.PHONY: up down logs ps airflow-user validate test-dgraph

up:
	docker-compose up -d --build

down:
	docker-compose down -v

logs:
	docker-compose logs -f --tail=200

ps:
	docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'

airflow-user:
	docker exec -it $$(docker ps --format '{{.ID}}\t{{.Image}}' | grep apache/airflow | awk '{print $$1}') \
	  airflow users create --username admin --password admin --firstname a --lastname b --role Admin --email a@example.com || true

validate:
	python3 scripts/validate_mcp.py

test-dgraph:
	python3 scripts/test_dgraph_flow.py
