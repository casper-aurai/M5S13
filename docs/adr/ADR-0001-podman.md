# ADR 0001: Use Podman for Container Orchestration

## Status
Accepted

## Context
FreshPOC is a data processing platform that requires containerized services for:
- Message queuing (Kafka)
- Graph database (Dgraph)
- Vector database (Weaviate)
- Object storage (MinIO)
- Log aggregation (Loki + Promtail)
- Monitoring (Prometheus + Grafana)
- Workflow orchestration (Airflow)
- Application services (ingestion, mining, analysis, etc.)

The team needs to choose a container runtime and orchestration tool that:
1. Provides a complete development and production environment
2. Supports all required services with proper networking and volumes
3. Enables easy local development and testing
4. Scales to production workloads
5. Integrates well with existing development workflows

## Decision
We will use **Podman** as our primary container runtime and orchestration tool for the following reasons:

### Podman Advantages
1. **Daemonless Architecture**: Unlike Docker, Podman doesn't require a daemon process, reducing attack surface and resource overhead
2. **Rootless by Default**: Containers can run as non-root users, improving security
3. **Docker Compatibility**: Podman is API-compatible with Docker, allowing easy migration from Docker Compose
4. **Built-in Compose Support**: Native support for docker-compose.yml files
5. **Better Security Model**: Stronger isolation and security boundaries compared to Docker
6. **Active Development**: Podman is actively maintained and developed by Red Hat

### Podman vs Docker Alternatives Considered
- **Docker + Docker Compose**: Current standard, but requires daemon and has larger attack surface
- **Docker + Kubernetes**: Overkill for development, too complex for initial setup
- **Podman Machine + Podman Compose**: Perfect balance of features and security
- **LXC/LXD**: Too low-level for application containers
- **systemd-nspawn**: Not suitable for application containers

## Consequences

### Positive
- **Enhanced Security**: Rootless containers and daemonless architecture improve security posture
- **Simplified Operations**: No daemon management required, easier troubleshooting
- **Better Resource Isolation**: Stronger process and network isolation
- **Future-Proof**: Podman is becoming the standard in enterprise environments
- **Developer Experience**: Familiar Docker Compose syntax with better security

### Negative
- **Learning Curve**: Team members may need to learn Podman-specific commands and concepts
- **Tool Ecosystem**: Some Docker-specific tools may not work directly with Podman
- **IDE Integration**: Some development tools may have better Docker integration than Podman

### Migration Strategy
1. **Phase 1 (Sprint 1)**: Set up Podman environment with all infrastructure services
2. **Phase 2 (Sprint 2-3)**: Migrate existing Docker workflows to Podman where applicable
3. **Phase 3 (Future)**: Evaluate Podman Desktop and advanced Podman features for enhanced developer experience

## Implementation Plan

### Infrastructure Setup
- Install Podman and podman-compose
- Configure user-specific Podman machine for development
- Set up proper networking and volume management
- Configure health checks for all services

### Development Workflow
- Use `podman-compose` for local development
- Leverage `podman machine` for consistent environments
- Implement proper logging and monitoring integration
- Create development shortcuts and automation scripts

### Production Considerations
- Podman is production-ready and used in enterprise environments
- Supports Kubernetes integration for future scaling needs
- Compatible with existing CI/CD pipelines through API compatibility

## Related ADRs
- ADR-0002: Airflow for Workflow Orchestration
- ADR-0003: Kafka for Message Queuing (pending)
- ADR-0004: Weaviate for Vector Storage (pending)

## References
- [Podman Documentation](https://docs.podman.io/)
- [Podman vs Docker Comparison](https://www.redhat.com/en/blog/podman-vs-docker)
- [Podman Security Features](https://www.redhat.com/en/blog/understanding-podman-security)
