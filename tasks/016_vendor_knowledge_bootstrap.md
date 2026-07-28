# Task 016

## Title

Anlogic DR1 vendor knowledge-base infrastructure bootstrap

## Status

In Progress

## Goal

Create the repository-side manifests, schemas, policies, documentation skeleton,
and local-only scripts needed to curate Anlogic DR1 vendor material without
copying private documents or changing the PC/ARM deployment implementation.

## Scope

This task only initializes knowledge-base infrastructure. It records supplied
source locations as unverified, defines provenance and conflict/duplicate
placeholders, documents source precedence, and provides read-only environment
and external-workspace bootstrap scripts. It does not ingest, parse, deduplicate,
or reconcile any vendor material.

## Allowed Files

- `.gitignore`
- `TASKS.md`
- `tasks/016_vendor_knowledge_bootstrap.md`
- `.knowledge/local_paths.example.yaml`
- `.knowledge/local_paths.yaml`
- `.knowledge/manifests/sources.yaml`
- `.knowledge/manifests/versions.yaml`
- `.knowledge/manifests/duplicates.yaml`
- `.knowledge/manifests/conflicts.yaml`
- `.knowledge/schemas/document_record.schema.yaml`
- `docs/vendor/SOURCE_POLICY.md`
- `docs/vendor/KNOWLEDGE_BASE_PLAN.md`
- `docs/vendor/CURRENT_BASELINE.md`
- `scripts/vendor/audit_environment.sh`
- `scripts/vendor/bootstrap_private_workspace.sh`

## Forbidden Files and Actions

- Do not create `.vendor/` in the repository.
- Do not copy or read vendor PDFs, SDKs, bitstreams, or source trees into the
  repository.
- Do not access the network, install software, or modify system configuration.
- Do not modify PC model/deployment code, PC evidence, or Tasks 001–015 states.
- Do not create ARM inference, cross-compilation, benchmark, or deployment code.
- Do not place passwords, tokens, private keys, or credentials in any file.
- Do not run the private-workspace bootstrap script during this task.
- Do not commit Git changes; the user requested a working-tree-only bootstrap.

## Commands

The scripts are intended to be run explicitly by a user after review:

```bash
bash scripts/vendor/audit_environment.sh
bash scripts/vendor/bootstrap_private_workspace.sh
```

The first command is read-only. The second creates only the documented
repository-external directory tree and copies nothing. Validation for this
bootstrap is limited to shell syntax, basic YAML structure, and whitespace
checks; no source retrieval or vendor processing is permitted.

## Acceptance Criteria

1. The next unused task number is used and no existing task file is overwritten.
2. The four source entries and version-freeze fields exist with unknown values
   where evidence is not available.
3. Duplicate/conflict manifests are empty structures with field descriptions.
4. The document-record schema contains every required provenance field.
5. Source precedence, staged plan, and known/unknown baseline are documented
   without inferred vendor facts.
6. `audit_environment.sh` is read-only, dependency-light, and does not expose
   credentials.
7. `bootstrap_private_workspace.sh` creates only the specified external paths
   and performs no copy or network operation.
8. The local-path file is ignored while manifests, schemas, and curated content
   remain trackable.
9. `bash -n` checks, basic YAML checks, and `git diff --check` pass.
10. Tasks 001–015 states and all PC evidence remain unchanged.

## Risks

- The supplied source paths, URLs, versions, and revisions have not been
  independently verified and must remain explicitly unverified.
- The local path file contains machine-specific paths and must never be
  committed.
- Empty knowledge directories are not represented by Git until a tracked file
  is added; this is intentional and avoids placeholder files.
- Native tooling, MinerU/qmd availability, and the board/toolchain remain
  unknown until a later, separately authorized audit.

## Execution Record

Initial infrastructure work is being performed on
`feature/vendor-knowledge-bootstrap`. No vendor material was read, copied, or
downloaded. No private workspace was created by the bootstrap script. The
remaining vendor facts are intentionally pending.
