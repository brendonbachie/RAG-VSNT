# Feature Specification: Offline RAG Commercial Platform

**Feature Branch**: `001-offline-rag-platform`

**Created**: 2026-05-16

**Status**: Draft

**Input**: User description: "Transformar o sistema RAG em um produto comercial para
organizações que precisam consultar documentação técnica sigilosa offline. Precisa ter:
interface web simples, autenticação de usuários, suporte a PDF/Word/Markdown, instalação
simples em qualquer máquina Windows ou Linux, logs de auditoria, e múltiplos modelos
Ollama. Tudo 100% offline, sem nenhum dado saindo da máquina."

---

## Clarifications

### Session 2026-05-16

- Q: Should the web server bind to localhost only or also be accessible from the local network? → A: Localhost-only (127.0.0.1). Accessible only from the machine running the server; no TLS required.
- Q: How are documents added to the system — folder drop only, web upload UI, or both? → A: Both methods: admin can drop files into `docs/` AND upload via the admin panel web UI; indexing triggers automatically after upload.
- Q: How is the first admin account created during installation? → A: Web-based setup wizard. On first browser access, the system detects no admin exists and presents a setup page; no terminal command needed.
- Q: How long should user sessions remain valid? → A: Configurable idle timeout with an 8-hour default. Admin can adjust the value in system settings; session expires after the configured period of inactivity.
- Q: What password complexity policy should be enforced at account creation? → A: No enforced complexity policy. Any non-empty password is accepted; the operator is responsible for choosing a strong password.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator Queries Documents via Web Interface (Priority: P1)

An operator opens a browser on the same machine running the system, logs in with their
credentials, and types a question in natural language. The system retrieves relevant
sections from the indexed documents and responds with an accurate, sourced answer. No
data leaves the machine at any point.

**Why this priority**: This is the core value proposition — replacing the terminal REPL
with an accessible web interface that any operator can use without technical knowledge.

**Independent Test**: Start the system on a fresh machine with sample documents, open the
browser, log in, and submit a question. Verify a sourced answer is returned without any
network activity leaving localhost.

**Acceptance Scenarios**:

1. **Given** the system is running and documents are indexed, **When** an operator enters
   a valid question in the web chat interface, **Then** the system returns an answer citing
   the source document and section, in under 60 seconds.
2. **Given** the operator asks about a topic not present in any indexed document, **When**
   the query is submitted, **Then** the system responds with "Não encontrei essa informação
   na documentação disponível." and does not fabricate content.
3. **Given** the system has no active internet connection, **When** a question is submitted,
   **Then** the system responds normally — no degradation or errors due to offline state.

---

### User Story 2 - Administrator Manages Users and Access (Priority: P2)

An administrator creates, activates, deactivates, and deletes user accounts through a web
admin panel. Each user is assigned a role (e.g., operator, admin). Operators can only
query; admins can also manage users and documents.

**Why this priority**: Multi-user access control is required for organizations deploying
this in shared or regulated environments.

**Independent Test**: Create an admin account during setup, log in, create a second
operator account, log in as that operator and confirm they cannot access the admin panel.

**Acceptance Scenarios**:

1. **Given** an admin is logged in, **When** they create a new user account with a role,
   **Then** the new user can log in and is restricted to their assigned role's permissions.
2. **Given** an admin deactivates a user account, **When** that user attempts to log in,
   **Then** login is rejected with a clear message.
3. **Given** an operator (non-admin) is logged in, **When** they attempt to access the
   admin panel URL directly, **Then** they are redirected to the main interface or shown
   an access-denied message.

---

### User Story 3 - Administrator Ingests Documents (PDF, Word, Markdown) (Priority: P2)

An administrator uploads new documents (PDF, DOCX, or Markdown) via the admin panel web
UI, or places them directly into the `docs/` folder. Either method triggers indexing
automatically (or via a single "Index Now" action). The documents become queryable
immediately after indexing, without restarting the system.

**Why this priority**: Supporting multiple document formats is essential for adoption in
organizations with heterogeneous documentation.

**Independent Test**: Drop a PDF and a DOCX file into `docs/`, trigger indexing, and
verify that questions whose answers exist only in those files are answered correctly.

**Acceptance Scenarios**:

1. **Given** a PDF or DOCX file is placed in `docs/`, **When** the administrator triggers
   indexing (via the admin panel or CLI), **Then** the documents are indexed and answerable
   within 5 minutes for files up to 50 MB.
2. **Given** a Markdown file with YAML frontmatter is indexed, **When** a query matches
   content from that file, **Then** the response cites the file name and section correctly.
3. **Given** a document is added while the system is running, **When** indexing completes,
   **Then** the document is available for queries without restarting the system.

---

### User Story 4 - System Produces Audit Logs (Priority: P3)

Every query submitted and every authentication event (login, logout, failed attempt) is
recorded in a local audit log file. Administrators can view recent logs from the admin
panel. Logs never leave the machine.

**Why this priority**: Required for regulated and defense environments where accountability
of information access must be demonstrable.

**Independent Test**: Submit 5 queries and perform 2 logins. Open the audit log and verify
each event is recorded with timestamp, user identity, and query text (or event type).

**Acceptance Scenarios**:

1. **Given** an operator submits a query, **When** the response is returned, **Then** the
   query text, the responding user's identity, and a timestamp are appended to the local
   audit log.
2. **Given** a user logs in successfully or fails to log in, **When** the event occurs,
   **Then** the event type, user identity, and timestamp are appended to the audit log.
3. **Given** an admin views the audit log panel, **When** the panel loads, **Then** the
   last 100 log entries are displayed in reverse chronological order.

---

### User Story 5 - Administrator Selects Active LLM Model (Priority: P3)

An administrator selects which locally installed Ollama model the system uses for
inference, from a list of models already available on the machine. The selection takes
effect on the next query without restarting the server.

**Why this priority**: Different models offer different speed/quality trade-offs; operators
should be able to switch without touching code.

**Independent Test**: With two Ollama models installed, switch the active model from the
admin panel and verify that the next query uses the new model (visible in the audit log or
response metadata).

**Acceptance Scenarios**:

1. **Given** multiple Ollama models are installed, **When** an admin selects a different
   model from the admin panel, **Then** subsequent queries use the newly selected model.
2. **Given** an admin selects a model that is not installed locally, **When** they attempt
   to save the selection, **Then** an error is displayed and the previous model remains
   active.
3. **Given** the active model is changed, **When** a query is submitted, **Then** no
   system restart is required for the change to take effect.

---

### User Story 6 - Simple Installation on Windows and Linux (Priority: P1)

A new user installs the system from scratch on a Windows or Linux machine with no prior
Python or RAG knowledge. The installation completes via a single script or documented
step-by-step process, and the system is queryable within 30 minutes on a machine with
internet access (for initial setup only).

**Why this priority**: Adoption depends entirely on ease of installation. A complex setup
process is a commercial blocker.

**Independent Test**: Follow the installation instructions on a clean Windows 11 VM and a
clean Ubuntu 22.04 VM. Verify the system is running and answering queries without
additional troubleshooting.

**Acceptance Scenarios**:

1. **Given** a clean machine with internet access, **When** the operator follows the
   installation guide, **Then** the system is running and answering queries within 30
   minutes.
2. **Given** the system is installed and set up, **When** the machine is disconnected from
   the internet and rebooted, **Then** the system starts normally and answers queries from
   the existing index.
3. **Given** the operator follows the installation guide on Windows, **Then** the same
   guide works on Linux without requiring OS-specific divergence beyond two or three
   clearly marked steps.

---

### Edge Cases

- What happens when a user uploads a corrupt or password-protected PDF?
- How does the system behave if Ollama crashes mid-query?
- What happens when the `docs/` folder contains thousands of large files (>1 GB total)?
- What if two administrators attempt to change the active model simultaneously?
- What happens when the disk is full and a new document is being indexed?

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a web-based chat interface accessible from a browser
  on the same machine only (bound to 127.0.0.1). No LAN or external network access is
  permitted; no TLS certificate is required.
- **FR-002**: The system MUST authenticate users with a username and password before
  granting access to any functionality. Any non-empty password MUST be accepted (no
  complexity policy is enforced; operators are responsible for choosing strong passwords).
  Sessions MUST expire after a configurable idle timeout (default: 8 hours).
  Administrators MUST be able to adjust the timeout value in system settings without
  restarting the server.
- **FR-003**: The system MUST support at least two roles: Operator (query only) and Admin
  (query + user management + document management + model selection).
- **FR-004**: The system MUST index and make queryable documents in PDF, DOCX, and
  Markdown formats.
- **FR-005**: The system MUST record every query and every authentication event to a local
  audit log file that never leaves the host machine.
- **FR-006**: The system MUST allow administrators to select the active Ollama model from
  the set of locally installed models without restarting the server.
- **FR-007**: The system MUST provide an installation procedure that works on both Windows
  and Linux without requiring pre-existing Python or Docker knowledge. The first admin
  account MUST be created through a web-based setup wizard triggered automatically on the
  first browser access, requiring no terminal interaction for account setup.
- **FR-008**: Responses MUST always cite the source document and section; when information
  is absent, the system MUST return the canonical "not found" phrase (Principle II).
- **FR-009**: Zero operational data MUST leave the host machine (Principle I).
- **FR-010**: The system MUST allow new documents to be added and indexed without a full
  system restart. Documents may be added by placing files directly in `docs/` (folder
  drop) or by uploading them through the admin panel web UI. In both cases, indexing
  MUST be triggered automatically or via a single admin action, with no restart required.

### Key Entities

- **User**: An authenticated person with a username, hashed password, role, and active
  status. Admins may manage other users.
- **Document**: A file (PDF, DOCX, or Markdown) stored in `docs/`, indexed into the
  vector store, with metadata (file name, section, frontmatter).
- **Query**: A natural-language question submitted by a user, together with the response,
  source nodes, and timestamp — persisted in the audit log.
- **AuditEvent**: A timestamped record of a query or authentication event, linked to the
  acting user's identity.
- **OllamaModel**: A locally installed Ollama model referenced by name; one is designated
  as active at any time.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator with no prior RAG or terminal experience can complete their first
  successful query within 5 minutes of first login.
- **SC-002**: The system answers queries sourced from indexed documents with no fabricated
  content in 100% of cases verifiable against the source documents.
- **SC-003**: Installation completes in under 30 minutes on a clean machine following the
  provided guide, verified on both Windows and Linux.
- **SC-004**: The system indexes a 50 MB PDF within 5 minutes on hardware meeting the
  recommended configuration.
- **SC-005**: Audit logs capture 100% of query and authentication events with no missing
  entries under normal operation.
- **SC-006**: Switching the active Ollama model takes effect on the next query without any
  system downtime.
- **SC-007**: The system operates fully without a network connection after initial setup,
  verified by disconnecting the machine and completing 10 consecutive queries.
- **SC-008**: An idle authenticated session is automatically invalidated after the
  configured timeout (default 8 hours), requiring re-authentication on the next request.

---

## Assumptions

- Users will have Ollama installed and at least one model downloaded before or during the
  installation procedure.
- The embedding model (BGE) and reranking model will be downloaded during setup (requires
  internet once); thereafter the machine may be air-gapped.
- The system is deployed on a single machine (not a distributed cluster); multi-machine
  deployments are out of scope for this version.
- The web interface is bound to 127.0.0.1 (localhost-only). It is not accessible from
  other machines on the network and is not exposed to the internet. No TLS certificate
  is required.
- User credentials are stored in a local database with industry-standard password hashing
  (bcrypt or equivalent); a more complex identity provider (LDAP, Active Directory) is out
  of scope for this version. No password complexity policy is enforced; operators are
  expected to choose appropriately strong passwords per their organization's policy.
- Document volume is assumed to be hundreds of files totaling up to a few gigabytes; very
  large corpora (>10 GB) may require hardware beyond the minimum spec.
- The first admin account is created via a web-based setup wizard: on the first browser
  access, the system detects no admin account exists and presents a setup page to define
  the admin username and password. No terminal command is required. No default credentials
  are shipped with the product.
