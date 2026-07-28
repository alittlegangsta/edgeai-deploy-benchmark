# Anlogic DR1 knowledge-base plan

The knowledge base is intentionally staged so that provenance and privacy are
reviewable before content is indexed.

## Phases

1. **Local material inventory** — inspect the user-authorized Milianke bundle
   in place, record filenames, hashes, sizes, and privacy notes, and copy only
   into the external private workspace when separately authorized.
2. **MinerU/qmd retrieval** — if the tools are available, convert and index
   private documents in the external workspace; record tool versions and keep
   caches outside the repository.
3. **Official repository freeze** — record exact Anlogic Wiki/repository
   snapshots, tags, branches, commits, and hashes before using examples or API
   claims.
4. **Wiki snapshots** — preserve dated, private snapshots with retrieval
   provenance; do not publish raw pages or credentials.
5. **Document-curation skill** — use a dedicated curator workflow to classify
   board, chip, SDK, NPU, build, and runtime material against the document
   record schema.
6. **Duplicate and conflict management** — compare hashes/content, populate
   the duplicate manifest, and record unresolved authority conflicts explicitly.
7. **Real-device evidence loop** — validate toolchain and runtime claims on the
   board, preserve command output and hashes, and link observations to source
   records.

Each phase stops when a required dependency, source identity, privacy decision,
or human approval is missing. No phase permits silent source substitution.
