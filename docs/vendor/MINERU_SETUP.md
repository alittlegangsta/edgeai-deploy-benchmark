# MinerU Document Explorer setup

This records the local setup used for document navigation only. No formal
vendor document was imported, no collection was registered, no vector embedding
was generated, and no cloud MinerU API was configured.

## Actual environment

- Node.js: `v22.22.3`
- npm: `10.9.8`
- Python: `3.12.3`
- Python virtual environment:
  `/home/dministrator/.venvs/mineru-document-explorer`
- MinerU Document Explorer npm package: `1.0.9`
- qmd executable:
  `/home/dministrator/.nvm/versions/node/v22.22.3/bin/qmd`
- qmd reported version: `1.0.9 (62387b8)`
- wrapper:
  `/home/dministrator/bin/qmd-dr1`

The Python packages installed in the dedicated environment are:

- `pymupdf==1.28.0`
- `python-docx==1.2.0`
- `python-pptx==1.0.2`

## MCP configuration

The project-local configuration is `.codex/config.toml`:

```toml
[mcp_servers.qmd]
command = "/home/dministrator/bin/qmd-dr1"
args = ["mcp"]
```

The existing `.codex/` ignore rule keeps this machine-specific configuration
out of Git.

## Installation commands used

```bash
python3 -m venv /home/dministrator/.venvs/mineru-document-explorer
/home/dministrator/.venvs/mineru-document-explorer/bin/python \
  -m pip install pymupdf python-docx python-pptx
npm install --global mineru-document-explorer
```

The npm prefix was the user-owned nvm prefix; no `sudo` or system installation
was used.

## Verification commands

```bash
/home/dministrator/bin/qmd-dr1 --help
/home/dministrator/bin/qmd-dr1 status
/home/dministrator/.venvs/mineru-document-explorer/bin/python - <<'PY'
import fitz
import docx
import pptx
print("document imports: PASS")
PY

/home/dministrator/bin/qmd-dr1 skill install
```

`qmd status` reported zero collections, zero indexed documents, and zero
vectors. The packaged skill was installed at
`.agents/skills/mineru-document-explorer`; the existing
`.agents/skills/dr1-vendor-doc-curator` directory was preserved.

Validation output is preserved outside the repository at:

```text
/home/dministrator/vendor/anlogic-dr1-knowledge/logs/mineru_setup.log
```

## Current boundaries

- Vector retrieval is not enabled; `qmd embed` has not been run.
- No embedding, reranking, or generation model was downloaded by this setup.
- No `MINERU_API_KEY` was set.
- Cloud MinerU parsing has not been used.
- No Milianke PDF or other formal vendor source has been copied or parsed.
- No Anlogic Wiki or Gitee repository was accessed.

## Uninstall and rollback

After reviewing generated state, the user may remove the local installation:

```bash
npm uninstall --global mineru-document-explorer
/home/dministrator/.venvs/mineru-document-explorer/bin/python \
  -m pip uninstall pymupdf python-docx python-pptx
rm -f /home/dministrator/bin/qmd-dr1
rm -rf /home/dministrator/.venvs/mineru-document-explorer
rm -rf .agents/skills/mineru-document-explorer
rm -f .codex/config.toml
```

The qmd status command may leave its empty local index at
`/home/dministrator/.cache/qmd/index.sqlite`; remove that cache only if the
user wants to reset qmd's local state. These rollback commands were documented,
not executed during setup.
