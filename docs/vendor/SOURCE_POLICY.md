# Vendor source policy

This policy defines how future Anlogic DR1 knowledge is curated. It does not
authorize downloading, copying, or publishing vendor material.

## Authority order

- Board physical interfaces, connectors, jumpers, and board-specific wiring
  use the Milianke board-level documentation first.
- Chip, SDK, NPU, runtime, and tool behavior use Anlogic official material
  first, including the official Wiki and matching source repositories.
- Build commands and API usage use source code whose tag or revision matches
  the SDK being evaluated.
- Logs captured on the real board are the final evidence for observed runtime
  behavior.

## Conflict and authenticity rules

- Never silently merge conflicting sources. Record the conflict and its
  resolution in the conflict manifest after explicit review.
- Do not invent SDK APIs, driver names, paths, parameters, addresses, bitstream
  requirements, or board capabilities.
- Preserve source identity, version/revision, retrieval time, file hash, and
  local private path before classifying a document.
- Private source material remains outside the repository; only reviewed small
  records and permitted summaries may be curated here.
