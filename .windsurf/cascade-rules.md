# FreshPOC Cascade Rules
# These rules ensure consistency, quality, and observability across the project

## Repository Hygiene Rules
- **README Updates**: When adding, modifying, or removing services, containers, or significant files, update README.md in the same commit
- **Health Checks**: Every new container/service must include a healthcheck in docker-compose.yml
- **Service Dependencies**: Document service dependencies clearly in docker-compose.yml comments
- **Port Management**: Track all exposed ports in README.md and ensure no conflicts

## Documentation Discipline Rules
- **ADR Generation**: For each new technology, architectural decision, or significant change, create an Architecture Decision Record (ADR) in /docs/adr/ADR-XXXX.md format
- **ADR Format**: Follow the standard ADR format (Title, Status, Context, Decision, Consequences)
- **Technology Documentation**: Document why specific technologies were chosen over alternatives
- **Quickstart Completeness**: Ensure README.md provides a complete, working quickstart for new contributors

## Observability-First Rules
- **Health Endpoints**: Every service must expose a /health endpoint that returns HTTP 200 when healthy
- **Metrics Endpoints**: Every service should expose a /metrics endpoint compatible with Prometheus
- **Prometheus Configuration**: When adding new services, update monitoring/prometheus.yml in the same PR
- **Logging Standards**: Use structured JSON logging for all services
- **Grafana Dashboards**: Create or update relevant Grafana dashboards for new services

## Atomic Commits Rules
- **Single Purpose**: Each commit should represent one logical change (new service, config update, documentation, etc.)
- **PR Linking**: Pull requests must link to relevant ADRs or backlog issues
- **Commit Messages**: Use conventional commit format: type(scope): description
- **No Mixed Changes**: Don't mix unrelated changes in a single commit

## Infrastructure as Code (IaC) Clarity Rules
- **Compose Organization**: Keep docker-compose.yml clean and organized by service type
- **DAG Organization**: Place Airflow DAGs in airflow/dags/ with clear naming
- **Monitoring Organization**: Keep Prometheus, Grafana, and Loki configs in monitoring/
- **Environment Separation**: Use docker/overrides/ for environment-specific configurations
- **Secrets Management**: Never commit secrets or credentials to version control

## Development Workflow Rules
- **Local Testing**: All changes must be tested locally before committing
- **Container Health**: Verify all containers start and pass health checks
- **Service Integration**: Test service-to-service communication for new endpoints
- **Documentation Verification**: Ensure all documented commands and endpoints work

## MCP Server Rules
- **Rule Governance**: Use the Cascade Rules MCP Server for centralized management of AI agent behavior rules
- **Health Endpoints**: Every MCP server must expose /health and /metrics endpoints
- **Container Operations**: Use the Podman MCP Server for all container management operations instead of direct podman/docker commands
- **State Management**: Use the Redis MCP Server for ephemeral agent state storage and inter-agent coordination
- **Task Management**: Use the Task Master Integration Server for GitHub Issues synchronization and task tracking

## Review and Merge Rules
- **Self-Review**: Authors should review their own changes before requesting review
- **Testing Evidence**: Include evidence of testing in PR descriptions
- **Documentation Updates**: Ensure all related documentation is updated
- **ADR References**: Reference relevant ADRs in PR descriptions for architectural changes
