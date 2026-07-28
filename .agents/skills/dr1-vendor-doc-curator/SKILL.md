---
name: dr1-vendor-doc-curator
description: >
  Curate evidence for Anlogic DR1/DR1M90 and MLK-F3P-CZ02 vendor documents,
  SDKs, Linux BSPs, NPU material, and board observations without inventing
  vendor facts.
---

# DR1 vendor document curator

## Trigger

Enable this skill when a task concerns any of the following:

- Anlogic DR1 or DR1M90
- MLK-F3P-CZ02 boards or core boards
- Linux BSP, Buildroot, or board images
- Native or cross compilation
- TD, FD, or SDK material
- NPU runtime, model conversion, or NPU IP
- Board interfaces, cameras, HDMI, or other board peripherals
- Vendor demonstration projects

## Required workflow

1. Read `.knowledge/manifests/versions.yaml` before making a version-sensitive
   statement.
2. Query the local private vendor knowledge base first, when a local source has
   been explicitly approved and indexed. Do not assume that a path in a
   manifest means that its contents have been read or copied.
3. For APIs, build commands, drivers, and file paths, continue checking source
   code from a repository revision that matches the recorded SDK tag or commit.
4. Classify every statement as one of:
   - **Document fact** — explicitly stated in an approved document.
   - **Source-code fact** — observed in a matching source revision.
   - **Engineering inference** — derived reasoning, clearly labeled as such.
   - **Real-device observation** — captured from a reproducible board command or
     log.
5. Do not invent APIs, driver names, toolchain parameters, memory addresses,
   device-tree nodes, model formats, or bitstream requirements.
6. Do not silently merge conflicting sources. Record each conflict and defer a
   decision until the authority and applicability have been reviewed.
7. Stop when an SDK tag does not match the repository tag or commit used for a
   claim. Do not substitute a latest branch or an unrecorded fork.
8. Treat real-device logs as the final authority for observed runtime behavior;
   documentation and source code do not replace a board observation.

## Evidence Brief

Curated work must produce an evidence brief with these fields:

```yaml
task: ""
board: ""
sdk_tag: ""
repository_tag_commit: ""
sources_consulted: []
documented_facts: []
source_code_facts: []
assumptions: []
conflicts: []
unresolved_blockers: []
proposed_action: ""
```

Empty or unknown values must remain explicit. Do not fill fields with inferred
versions, paths, addresses, or capabilities.

## Provenance and safety

- Preserve source IDs, paths, revision identifiers, retrieval time, file size,
  and SHA256 in the manifests before content is curated.
- Keep vendor PDFs, SDKs, source trees, credentials, and board logs outside the
  repository unless a task explicitly authorizes a small derived record.
- Respect `approved_for_copy` and `index_status` in the document manifest.
- A metadata-only inventory is not a document reading or indexing result.
- Never use a document title alone to establish board applicability, SDK
  version, runtime support, or hardware capability.
