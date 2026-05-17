<!--
SYNC IMPACT REPORT
==================
Version change: [template] → 1.0.0
Initial constitution — all sections populated from project context.

Modified principles: N/A (first fill)

Added sections:
  - Core Principles (5 principles defined)
  - Security & Compliance Requirements
  - Development Workflow
  - Governance

Removed sections: N/A

Templates requiring updates:
  ✅ .specify/templates/plan-template.md — Constitution Check gates align with principles
  ✅ .specify/templates/spec-template.md — no structural changes required
  ✅ .specify/templates/tasks-template.md — observability / offline-compliance task types added as notes

Follow-up TODOs:
  - TODO(RATIFICATION_DATE): confirm original adoption date with project lead if prior to 2026-05-16
-->

# RAG VSNT Constitution

## Core Principles

### I. Offline-First (NON-NEGOTIABLE)

Zero bytes of operational data MUST leave the host machine during normal use.
All components — LLM inference, embeddings, reranking, index storage — MUST run
locally. No telemetry, no cloud APIs, no external DNS lookups are permitted at
runtime. The system MUST function completely inside an air-gapped environment
after the one-time setup phase.

- LLM inference MUST use Ollama on localhost (port 11434).
- Embeddings MUST use locally cached HuggingFace models (BAAI/bge-* family).
- Reranking MUST use a locally cached cross-encoder model.
- The vector index MUST persist to disk (`.rag_index/`) and never be transmitted.
- Setup-time downloads (models, pip packages) are the only permitted outbound
  traffic; once setup is complete the machine MAY be fully disconnected.

### II. Accuracy Over Completeness

The system MUST prioritize factual accuracy over answer completeness.
Hallucinated technical data — measurements, procedures, specifications — are
mission-critical failures in a defense context.

- Responses MUST cite the source document and section for every factual claim.
- When the requested information is absent from the indexed documents, the system
  MUST respond with the exact phrase: "Não encontrei essa informação na
  documentação disponível." No approximations or inferences are permitted.
- LLM temperature MUST remain ≤ 0.2 to minimize creative generation.
- Numerical values and specifications MUST be rendered as tables, not prose.
- Procedural information MUST be rendered as numbered steps.

### III. Security by Design

The system handles classified defense documentation and MUST treat every layer
as a potential attack surface.

- Documents in `docs/` and the index in `.rag_index/` MUST be stored on
  encrypted media (LUKS / BitLocker) in classified environments.
- Physical access to the host machine MUST be controlled.
- Query logs SHOULD be enabled for auditability; log files MUST remain local.
- No user-supplied content (queries) may be written back to the document index.
- Dependencies MUST be pinned with version floors (`>=`) and SHOULD be audited
  before air-gap transfer to prevent supply-chain tampering.

### IV. Retrieval Quality

Search quality is the primary determinant of response accuracy. The retrieval
pipeline MUST be multi-stage to maximize precision.

- Retrieval MUST combine semantic search (BGE vector embeddings) with keyword
  search (BM25) fused via Reciprocal Rank Fusion (RRF).
- A cross-encoder reranker MUST post-process candidates and reduce them to
  `RERANK_TOP_N` (default 3) before sending context to the LLM.
- Chunk size MUST be ≤ 512 tokens with ≥ 50-token overlap to preserve context
  across section boundaries.
- YAML frontmatter in source documents SHOULD be parsed and stored as metadata
  to enable structured filtering; noisy metadata keys MUST be excluded from
  embeddings and LLM context via the exclusion lists.
- The index MUST auto-detect embedding dimension mismatches and rebuild itself
  rather than serving stale or corrupt embeddings.

### V. Operational Simplicity

The system MUST be operable by a single operator without specialized ML
knowledge. Complexity that does not directly improve retrieval quality or
security is prohibited.

- The primary interface MUST be a terminal REPL requiring only `python
  rag_vsnt_offline.py` to start.
- Switching the LLM MUST require editing exactly one constant (`OLLAMA_MODEL`)
  and deleting the index directory — no other code changes.
- Error messages MUST include the corrective command (e.g., `ollama serve`,
  `ollama pull <model>`).
- Conversational context MUST be maintained within a session via
  `ChatMemoryBuffer`; operators MUST be able to reset it with the command
  `limpar` without restarting the process.
- Additional interfaces (e.g., Streamlit web UI) are permitted but MUST NOT
  compromise the offline-first or security principles.

## Security & Compliance Requirements

These requirements apply to all environments where VSNT documentation is indexed.

- **Air-gap compatibility**: After initial setup, the system MUST operate with
  no network interface active.
- **Model transfer**: Models MUST be transferred to air-gapped machines via
  `ollama save` / `ollama load` or HuggingFace cache copy — never via
  internet-connected package managers.
- **Dependency audit**: Before any `pip install` on a classified machine, the
  package set MUST be reviewed for unexpected network calls or telemetry.
- **Log retention**: Query logs MUST be retained per the Marinha do Brasil's
  information security policy; the default `manage_index.py` logging hook
  satisfies this requirement when enabled.
- **Index integrity**: The `.rag_index/` directory MUST be treated with the same
  classification level as the source documents in `docs/`.

## Development Workflow

- **Dependency changes**: Any addition to `requirements_offline.txt` MUST be
  verified for offline compatibility before merging. Test by running with no
  network access.
- **Document ingestion**: New documents added to `docs/` are indexed on the next
  startup if the index is deleted, or via `manage_index.py` for incremental
  updates.
- **Model upgrades**: When changing `OLLAMA_MODEL` or `EMBED_MODEL`, delete
  `.rag_index/` and reindex. Validate accuracy with at least three representative
  test queries before deploying.
- **Code changes to the retrieval pipeline**: MUST be validated end-to-end
  (query → retrieval → reranking → response) in an offline environment before
  release.
- **Versioning**: Follow semantic versioning. MAJOR bumps for retrieval pipeline
  architecture changes; MINOR for new features (UI, new document types); PATCH
  for bug fixes and dependency updates.
- **Commits**: Each logical change (config tweak, new feature, bug fix) MUST be
  committed separately with a descriptive message.

## Governance

This constitution supersedes all other development practices for the RAG VSNT
project. It represents the non-negotiable constraints agreed upon by the project
team and approved by the technical lead.

**Amendment procedure**:
1. Propose amendment in writing, citing the principle affected and the rationale.
2. Verify the proposed change does not violate Principle I (Offline-First) or
   Principle III (Security by Design) — these two principles are immutable
   without explicit authorization from the Marinha do Brasil information security
   authority.
3. Update this file, increment the version, and update `LAST_AMENDED_DATE`.
4. Propagate changes to all dependent templates (`.specify/templates/`).
5. Commit with message: `docs: amend constitution to vX.Y.Z (<summary>)`.

**Versioning policy**: MAJOR.MINOR.PATCH per semantic versioning rules defined
in the Development Workflow section.

**Compliance review**: Every feature plan (`plan.md`) MUST include a
"Constitution Check" section that gates Phase 0 research. Non-compliance MUST be
documented in the Complexity Tracking table with explicit justification.

**Runtime guidance**: See `README.md` and `README_offline.md` for operator
instructions. See `manage_index.py` for index management procedures.

**Version**: 1.0.0 | **Ratified**: 2026-05-16 | **Last Amended**: 2026-05-16
