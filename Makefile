# FreshPOC Developer Makefile
# Provides shortcuts for common development and operations tasks

.PHONY: help up down logs clean restart status health topics ui shell format lint test docs adr

# Default target
help:
	@echo "FreshPOC Development Environment"
	@echo "================================"
	@echo ""
	@echo "Available commands:"
	@echo "  make up          - Start all services with Podman Compose"
	@echo "  make down        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make logs        - Show logs from all services"
	@echo "  make logs-follow - Follow logs from all services"
	@echo "  make status      - Show status of all containers"
	@echo "  make health      - Check health of all services"
	@echo "  make clean       - Stop services and remove all data"
	@echo "  make topics      - List Kafka topics"
	@echo "  make kafka-ui   - Open Kafka UI in browser"
	@echo "  make grafana    - Open Grafana in browser"
	@echo "  make airflow    - Open Airflow UI in browser"
	@echo "  make shell       - Open shell in a running container"
	@echo "  make format      - Format code with black and isort"
	@echo "  make lint        - Run linting checks"
	@echo "  make test        - Run tests"
	@echo "  make docs        - Generate documentation"
	@echo "  make adr         - Generate ADRs for recent changes"
	@echo ""

# ========================================
# SERVICE MANAGEMENT
# ========================================

up:
	@echo "Starting FreshPOC infrastructure stack..."
	podman-compose -f docker/docker-compose.yml up -d
	@echo "Waiting for services to be healthy..."
	@sleep 10
	@make health

down:
	@echo "Stopping all services..."
	podman-compose -f docker/docker-compose.yml down

restart:
	@echo "Restarting all services..."
	podman-compose -f docker/docker-compose.yml restart

logs:
	podman-compose -f docker/docker-compose.yml logs

logs-follow:
	podman-compose -f docker/docker-compose.yml logs -f

status:
	@echo "Container status:"
	podman ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

health:
	@echo "Checking service health..."
	@for service in kafka dgraph-alpha weaviate minio loki prometheus grafana postgres redis; do \
		echo -n "Checking $$service: "; \
		if podman exec freshpoc-$$service curl -f -s http://localhost:$$(podman port freshpoc-$$service | head -1 | cut -d: -f2)/health > /dev/null 2>&1; then \
			echo "✓ Healthy"; \
		else \
			echo "✗ Unhealthy"; \
		fi; \
	done

# ========================================
# SERVICE ACCESS
# ========================================

kafka-ui:
	@echo "Opening Kafka UI..."
	@which open >/dev/null && open http://localhost:8080 || echo "Open http://localhost:8080 in your browser"

grafana:
	@echo "Opening Grafana..."
	@which open >/dev/null && open http://localhost:3000 || echo "Open http://localhost:3000 in your browser (admin/freshpoc-grafana)"

airflow:
	@echo "Opening Airflow UI..."
	@which open >/dev/null && open http://localhost:8083 || echo "Open http://localhost:8083 in your browser"

# ========================================
# DATA MANAGEMENT
# ========================================

topics:
	@echo "Kafka topics:"
	podman exec freshpoc-kafka kafka-topics --bootstrap-server localhost:9092 --list

clean:
	@echo "Cleaning up all data and containers..."
	podman-compose -f docker/docker-compose.yml down -v
	podman volume prune -f
	podman system prune -f
	@echo "Removing local data directories..."
	rm -rf data/
	rm -rf reports/generated/

# ========================================
# DEVELOPMENT TOOLS
# ========================================

shell:
	@echo "Available containers:"
	@podman ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
	@echo ""
	@echo "Usage: podman exec -it <container_name> /bin/bash"

format:
	@echo "Formatting Python code..."
	black servers/ services/ airflow/ --line-length 88
	isort servers/ services/ airflow/ --profile black

lint:
	@echo "Running linting checks..."
	flake8 servers/ services/ airflow/ --max-line-length 88 --extend-ignore E203,W503
	mypy servers/ --ignore-missing-imports

test:
	@echo "Running tests..."
	pytest servers/ -v

# ========================================
# DOCUMENTATION
# ========================================

docs:
	@echo "Generating documentation..."
	@echo "TODO: Implement documentation generation"

adr:
	@echo "Generating ADRs for recent changes..."
	@echo "TODO: Implement ADR generation based on recent commits"

# ========================================
# UTILITIES
# ========================================

# Show service URLs and access information
info:
	@echo "FreshPOC Service Access Information"
	@echo "=================================="
	@echo ""
	@echo "Kafka UI:        http://localhost:8080"
	@echo "Grafana:         http://localhost:3000 (admin/freshpoc-grafana)"
	@echo "Airflow UI:      http://localhost:8083"
	@echo "Dgraph Ratel:    http://localhost:8081"
	@echo "Weaviate:        http://localhost:8082"
	@echo "MinIO Console:   http://localhost:9001 (freshpoc-admin/freshpoc-password)"
	@echo ""
	@echo "Kafka Broker:    localhost:9092"
	@echo "PostgreSQL:      localhost:5432 (airflow/airflow)"
	@echo "Redis:           localhost:6379"
	@echo ""
	@echo "Prometheus:      http://localhost:9090"
	@echo "Loki:            http://localhost:3100"

# Quick setup for new contributors
setup:
	@echo "Setting up development environment for new contributors..."
	@echo "1. Ensure Podman is installed and running"
	@echo "2. Run: make up"
	@echo "3. Wait for all services to be healthy"
	@echo "4. Access services using the URLs above"
	@echo "5. Run: make airflow to access Airflow UI"
	@echo ""
	@echo "For detailed setup instructions, see README.md"
