# [WAVE2-C] Reporting Service - Markdown + Mermaid + MinIO

**Labels:** `reporting`, `p1-high`, `wave2-poc`, `ready-for-dev`

## Objective
Implement reporting service that generates Markdown reports with Mermaid diagrams from Dgraph data and stores artifacts in MinIO.

## Background
Need to create human-readable reports showing analysis results, KPIs, and visual representations of the code graph structure.

## Tasks

### 1. Reporting Service Core
- [ ] Create `/generate` endpoint in reporting service
- [ ] Query Dgraph for repository and file data
- [ ] Generate comprehensive report with KPIs and visualizations

### 2. Report Content Structure
- [ ] **KPI Block**: Repository count, file count, author statistics
- [ ] **Mermaid Graph**: Visual representation of repo → files → findings relationships
- [ ] **Metadata**: Deterministic timestamps and content hash in footer

### 3. MinIO Integration
- [ ] Upload reports to `fresh-reports/` bucket
- [ ] Store `latest/latest.md` and `latest/diagram.mmd` files
- [ ] Ensure proper file versioning and organization

### 4. Report Template
- [ ] Create reusable Markdown template with:
  - Header with generation timestamp
  - KPI summary section
  - Mermaid diagram section
  - Footer with content hash and metadata

## Dgraph Query Specification

```graphql
{
  q(func: has(file)) {
    uid
    file
    lang
    repo: ~belongs_to {
      repo
    }
    findings_count: count(~uses)
  }
}
```

## Report Format Example

```markdown
# Code Analysis Report

**Generated:** 2024-01-01T12:00:00Z
**Content Hash:** sha256:abc123...

## KPIs

- **Repositories:** 5
- **Total Files:** 150
- **Python Files:** 89
- **SQL Files:** 61
- **Top Language:** Python (59.3%)

## Repository Structure

\`\`\`mermaid
graph TD
    A[dbt-labs/jaffle-shop] --> B[models/]
    A --> C[tests/]
    B --> D[orders.sql]
    B --> E[customers.sql]
    D --> F[tables: orders, customers]
    E --> G[tables: customers]
\`\`\`

## File Details

| Repository | File | Language | Findings |
|------------|------|----------|----------|
| dbt-labs/jaffle-shop | models/orders.sql | sql | 3 |
| dbt-labs/jaffle-shop | models/customers.sql | sql | 2 |

---
*Report ID: rpt_20240101_120000_abc123*
```

## API Specification

### GET /generate
**Response:** 200 OK with report generation details
```json
{
  "status": "success",
  "report_path": "fresh-reports/latest/latest.md",
  "diagram_path": "fresh-reports/latest/diagram.mmd",
  "timestamp": "2024-01-01T12:00:00Z",
  "content_hash": "sha256:abc123..."
}
```

## Acceptance Criteria

- [ ] `curl http://localhost:8016/generate` returns 200
- [ ] MinIO console shows `fresh-reports/latest.md` with updated content
- [ ] Report contains accurate counts matching Dgraph data
- [ ] Mermaid diagram renders correctly
- [ ] Content hash is deterministic for same data

## Dependencies
- Dgraph running and populated with data
- MinIO running and accessible
- Existing reporting service structure
- Python MinIO client library

## Risk Mitigation
- Ensure deterministic report generation for testing
- Handle cases where Dgraph is empty gracefully
- Implement proper error handling for MinIO operations