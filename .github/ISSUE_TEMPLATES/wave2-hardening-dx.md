# [WAVE2-F] Hardening + Developer Experience

**Labels:** `dx`, `p2-medium`, `wave2-poc`, `ready-for-dev`

## Objective
Improve development workflow, add quality gates, and enhance overall developer experience for the Wave 2 implementation.

## Background
Need proper tooling and automation to ensure code quality, easy testing, and smooth development workflow.

## Tasks

### 1. Makefile Enhancements
- [ ] Add `make topics` target to create Kafka topics idempotently
- [ ] Add `make demo` target for full pipeline demo
- [ ] Ensure all existing `make` targets work correctly
- [ ] Add `make help` for target documentation

### 2. Demo Target Implementation
- [ ] `make demo` should:
  - Verify all services are healthy
  - Create necessary Kafka topics
  - Run one full DAG execution
  - Print locations of generated artifacts
  - Show relevant logs and metrics

### 3. Pre-commit Hooks
- [ ] Configure pre-commit with:
  - `black` for code formatting
  - `ruff` for linting
  - `mypy --ignore-missing-imports` for type checking
- [ ] Apply to all Python services
- [ ] Ensure hooks run on staged changes

### 4. Health Check Improvements
- [ ] Ensure all services have `/health` endpoints
- [ ] Add Docker Compose healthchecks for all services
- [ ] Implement proper health check logic:
  - Database connectivity
  - Kafka connectivity (where applicable)
  - External service dependencies

### 5. Seed Script Creation
- [ ] Create `scripts/seed_minio.py` script
- [ ] Script should populate `fresh-reports/` bucket with:
  - Logo/readme files
  - Sample report structure
  - Initial diagram templates

### 6. Development Documentation
- [ ] Update README with Wave 2 setup instructions
- [ ] Document local development workflow
- [ ] Add troubleshooting section for common issues

## Makefile Targets Specification

```makefile
.PHONY: topics demo help

# Create Kafka topics idempotently
topics:
	@echo "Creating Kafka topics..."
	kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists \
		--topic repos.ingested --partitions 3 --replication-factor 1
	kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists \
		--topic code.mined --partitions 3 --replication-factor 1
	# ... other topics

# Run full pipeline demo
demo: up topics
	@echo "Running demo pipeline..."
	# Trigger ingestion
	curl -X POST "http://localhost:8011/trigger?repo=https://github.com/dbt-labs/jaffle-shop-classic"
	# Wait for completion and show results
	@echo "Demo complete! Artifacts available at:"
	@echo "- Reports: http://localhost:9001/fresh-reports/latest.md"
	@echo "- Grafana: http://localhost:3000"
	@echo "- Dgraph: http://localhost:8000"

# Show available targets
help:
	@echo "Available targets:"
	@echo "  up        - Start all services"
	@echo "  down      - Stop all services"
	@echo "  topics    - Create Kafka topics"
	@echo "  demo      - Run full pipeline demo"
	@echo "  logs      - Show service logs"
```

## Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.0.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/astral-sh/ruff
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--ignore-missing-imports]
```

## Acceptance Criteria

- [ ] `make demo` runs successfully and prints artifact locations
- [ ] `make topics` creates all required Kafka topics without errors
- [ ] Pre-commit hooks pass on all service code
- [ ] All services respond to `/health` requests appropriately
- [ ] Docker Compose healthchecks pass for all services
- [ ] Seed script successfully populates MinIO bucket

## Dependencies
- Existing Makefile structure
- Docker Compose configuration
- Python services with proper structure
- Kafka, MinIO, and other infrastructure services

## Risk Mitigation
- Test all make targets thoroughly before committing
- Ensure pre-commit hooks don't break existing code
- Make health checks lightweight to avoid performance impact