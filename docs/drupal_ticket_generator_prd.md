# Drupal Ticket Generator â€” Product Requirements Document

**Version:** 1.0  
**Date:** December 26, 2025  
**Purpose:** Handoff companion for Claude Code development

---

## 1. Problem Statement

After completing a Drupal technical specification, the development director must manually create Jira tickets for each configuration component (content types, fields, views, workflows, etc.). This process is time-consuming, resulting in tickets with minimal descriptions that omit useful context.

The specification spreadsheets already contain the configuration details developers need, but extracting that information during implementation is tedious. Developers must cross-reference spreadsheets while building, and lack clear success criteria for self-QA.

**This tool automates ticket generation by:**

1. Parsing configuration data from CSV exports of the tech spec
2. Using LLM processing to synthesize each component into a structured ticket containing:
   - A one-sentence user story (end-user or administrator perspective)
   - Configuration settings organized as a reference table
   - Success criteria for developer self-verification
3. Preserving entity relationships as Jira ticket dependencies
4. Exporting directly to Jira with proper ordering and linking

**Primary trigger:** New site builds and extensive site overhauls, after tech spec completion.

---

## 2. Users & Roles

### Primary User: Development Director

- Writes the technical specifications that become input CSVs
- Frontend developer; tech-savvy and frequently does development and support work directly
- Familiar with Drupal entity structures, CSV formats, and Jira administration
- Comfortable with OAuth flows and interpreting technical validation errors
- Can resolve user-fixable issues and frontend concerns; backend/infrastructure issues would be escalated to the team

### Usage Pattern

- Single user at a time (concurrent multi-user support not required for initial release)
- Typical workflow: complete tech spec â†’ export CSVs â†’ generate tickets â†’ review/edit â†’ export to Jira
- Sessions may span multiple sittings (session recovery is important)

### Ticket Consumers

- Generated tickets are assigned to a team of up to 5 people:
  - 3 developers
  - Development director
  - Technical director
- Consumers need tickets with clear configuration tables and success criteria for self-QA

### Role Model

- Single role; no permission differentiation required
- All authenticated users have full access to all features

### Future Consideration

- Multi-user support (e.g., project manager access) may be needed in 1-2 years
- Current architecture should not preclude this, but it's not a Phase 1 requirement

---

## 3. User Journey Overview

The workflow is a linear progression through six stages. Sessions may span multiple sittings, but the path is sequential â€” users cannot skip stages or work out of order.

### Stage 1: Site Info Collection

**User action:** Authenticate via Jira OAuth, then provide:
- Project name (e.g., "UWEC Website Rebuild")
- Project description (brief context for LLM ticket generation)
- Jira project key (e.g., "ZTEST")

**System behavior:** Validates Jira project access and caches project metadata (sprints, team members) for later assignment.

**User expectation:** Quick setup step; should take under a minute.

---

### Stage 2: Upload

**User action:** Upload all CSV files from the tech spec at once (batch upload from Google Sheets export).

**System behavior:**
- Auto-detects CSV types (bundles, fields, views, etc.)
- Validates schema and cross-file relationships
- Reports all errors with actionable guidance

**User expectation:** Usually works on first attempt with well-formed tech specs. Validation errors should be clear enough to fix without assistance.

**Typical volume:** 5-15 CSV files per session.

---

### Stage 3: Processing

**User action:** Initiate ticket generation; wait for completion.

**System behavior:**
- LLM processes each entity group, generating ticket content with:
  - One-sentence user story
  - Configuration reference table
  - Success criteria
- Progress updates via WebSocket (with REST polling fallback)

**User expectation:** 10-15 minutes for a typical tech spec. Real-time progress feedback is important given the duration.

---

### Stage 4: Review

**User action:** Review generated tickets; make light edits as needed.

**System behavior:**
- Displays tickets grouped by entity type
- Supports inline editing of title, description, assignments
- Auto-generates attachments for oversized content (>30k characters)
- Validates ADF format before allowing export

**User expectation:** Light touch-ups, not significant rewriting. Dependency management is mostly automatic; manual adjustment only needed for obscure relationships.

---

### Stage 5: Jira Export

**User action:** Initiate export; wait for completion.

**System behavior:**
- Creates tickets sequentially in dependency order
- Uploads attachments
- Creates Jira issue links for dependencies
- Progress updates via WebSocket

**User expectation:** A few minutes depending on ticket count. Failures should clearly indicate whether retry is possible.

---

### Stage 6: Completed

**User action:** None â€” session is finished.

**System behavior:** Session marked complete; data retained per cleanup policy (7 days).

**User expectation:** Any further edits happen directly in Jira. No need to return to this tool for the exported tickets.

---

## 4. Success Criteria

### Time Savings

- Manual ticket generation for a new build currently takes 6-8+ hours
- Target: Reduce to ~1 hour (upload through export completion)
- Typical session should complete in under 45 minutes; maximum acceptable duration is 1 hour

### Content Quality

- **80% of tickets should require no editing**
- Acceptable edits: Minor adjustments to user story tone or success criteria wording
- Unacceptable: Factual errors in the configuration reference table

*Quality note:* The reference table section is data extraction from source CSVs, not LLM interpretation. This section should be accurate by construction. LLM value-add is in synthesizing user stories and success criteria from the raw configuration data.

### Reliability

- Processing success rate: â‰¥95% with valid input files
- Jira export success rate: â‰¥95% with validated tickets
- Partial export is acceptable (resume from failure point); complete data loss is not

### Recovery

- On failure: Retry from the failure point, not from the beginning
- Session persistence: User can close browser and resume session later (survives power failure, browser crash)
- Recovery window: Sessions remain recoverable for 7 days

### Validation Quality

- Validation errors must be actionable: User should be able to fix issues without external assistance
- Error messages should reference specific files, rows, and fields where applicable

---

## 5. Scope Boundaries

### In Scope (Phase 1)

| Capability | Notes |
|------------|-------|
| CSV file upload | Batch upload from Google Sheets export |
| Auto-detection of CSV types | Based on filename and content patterns |
| LLM-powered ticket generation | User story, configuration table, success criteria |
| Dependency detection | Automatic based on Drupal entity relationships |
| Manual dependency adjustment | For obscure relationships not auto-detected |
| Ticket review and editing | Inline editing with auto-save |
| Jira export with linking | Sequential creation with dependency links |
| Session recovery | Resume from browser close or failure |
| Single Jira instance | Hardcoded to `ecitizen.atlassian.net` |
| Single Jira issue type | Task only |

### Out of Scope (Phase 1)

| Capability | Rationale |
|------------|-----------|
| Multi-user concurrent sessions | Single user at a time is sufficient for current team size |
| Role-based permissions | Single role; all users have full access |
| Multiple Jira instances | Only used for Electric Citizen projects |
| Selective ticket export | All-or-nothing per session; simplifies state management |
| Post-export editing | Changes happen directly in Jira |
| Historical reporting/analytics | Adds complexity without clear Phase 1 value |

### Future Enhancements

| Capability | Description |
|------------|-------------|
| Google Sheets integration | Extract data directly via URL instead of requiring CSV export; would require Google OAuth and Sheets API |
| Ticket category assignment | LLM categorizes tickets as Front End / Site Building / Back End; user maps categories to team members for bulk assignment |
| Multi-user support | Concurrent sessions for project manager access (anticipated need in 1-2 years) |
| Multiple Jira issue types | Support for Story, Bug, etc. if workflows expand |

---

## 6. Constraints & Assumptions

### Technical Constraints

| Constraint | Detail |
|------------|--------|
| Jira API rate limiting | 1.5-second delay between ticket creation calls (conservative estimate; may be tunable) |
| Jira field limits | ~30,000 character limit for description field; oversized content becomes attachment |
| File upload limits | 2MB per file, 50MB total per session, maximum 25 files |
| Single Jira instance | Hardcoded to `ecitizen.atlassian.net` |
| LLM API dependencies | Requires external API access to OpenAI and/or Anthropic |

### Business Constraints

| Constraint | Detail |
|------------|--------|
| Single concurrent user | Architecture optimized for one active session at a time |
| Small team | 7-person team; 5 ticket consumers maximum |
| Cost efficiency | LLM session costs must be small enough to justify time savings |

### Infrastructure Assumptions

| Assumption | Detail |
|------------|--------|
| Cloud hosting | AWS or similar cloud provider |
| Modern browsers | Chrome primary; no legacy browser support required |
| Persistent storage | PostgreSQL for session/ticket data; Redis for task queue and pub/sub |
| Background processing | ARQ workers for LLM processing and Jira export |

### Data Assumptions

| Assumption | Detail |
|------------|--------|
| Non-sensitive data | CSV files contain build specifications only; no PII or confidential client data |
| 7-day retention | Sessions and associated data cleaned up after 7 days |
| No compliance requirements | No special data handling regulations apply |

### Dependency Assumptions

| Assumption | Detail |
|------------|--------|
| Jira Cloud availability | Tool depends on Jira Cloud API being accessible |
| LLM provider availability | At least one configured LLM provider must be operational |
| Valid OAuth credentials | User must have Jira account with project access and CREATE_ISSUES permission |
| Well-formed CSV input | Input files follow expected Drupal export patterns; garbage-in-garbage-out applies |

---

## 7. Non-Functional Requirements

**Context:** This tool is used occasionally for new site builds and major overhauls. It also serves as a proof-of-concept for AI-assisted application development. Requirements are calibrated accordingly.

### Availability

| Requirement | Target |
|-------------|--------|
| Uptime | No formal SLA; occasional downtime acceptable |
| Maintenance | Can be taken offline as needed; no 24/7 requirement |
| Recovery | Session recovery handles most interruptions gracefully |

### Performance

| Requirement | Target |
|-------------|--------|
| Page load / API response | Standard web app expectations; no hard limits |
| LLM processing | 10-15 minutes acceptable; faster is better |
| Jira export | Bounded by API rate limits (~1.5 sec/ticket) |
| Progress feedback | Real-time updates during long operations (WebSocket preferred, REST polling fallback) |

### Security

| Requirement | Implementation |
|-------------|----------------|
| Authentication | Jira OAuth 2.0 with PKCE |
| Token storage | Fernet symmetric encryption at rest |
| Transport | HTTPS only |
| Session security | HTTP-only, secure, same-site cookies |
| Audit logging | Standard audit log for debugging; no compliance requirements |

*Note: No special security requirements beyond standard web application practices. Data is non-sensitive build specifications.*

### Data Management

| Requirement | Implementation |
|-------------|----------------|
| Retention | 7-day automatic cleanup for sessions and associated data |
| Backup | Regular database snapshots |
| Recovery | Snapshot restore acceptable; point-in-time recovery not required |

### Deployment

| Requirement | Implementation |
|-------------|----------------|
| Container platform | Docker / Docker Compose |
| Services | API (FastAPI), Worker (ARQ), PostgreSQL, Redis |
| Environment parity | Development and production use same container definitions |
| Configuration | Environment variables for all deployment-specific settings |
| Orchestration | Docker Compose sufficient; Kubernetes not required |

### Monitoring & Operations

| Requirement | Implementation |
|-------------|----------------|
| Alerting | None required; "check when something seems wrong" |
| Logging | Application logs for debugging; no centralized log aggregation required |
| Health checks | Basic endpoint health for deployment verification |

### Browser Support

| Requirement | Target |
|-------------|--------|
| Primary | Chrome (current versions) |
| Secondary | Modern browsers (Firefox, Safari, Edge) |
| Excluded | Legacy browsers, IE |

---

## Document References

This PRD accompanies detailed technical documentation. See the following for implementation specifics:

**Architecture & Patterns:**
- `Comprehensive_Updated_Directory_Structure_updated.md`
- `fastapi_di_lifecycle_decisions_updated.md`
- `repository_patterns_decisions_updated.md`
- `background_task_infrastructure.md`

**Phase Instructions:**
- `phase_1_foundation_infrastructure.md`
- `phase_2_authentication_session.md`
- `phase_3_file_upload_validation.md`
- `phase_4_processing_ticket_generation.md`
- `phase_5_review_stage.md`
- `phase_6_jira_export.md`

**Conflict Resolution:**
- `documentation_review_decisions.md`
- `discrepancy_resolution_decisions.md`
