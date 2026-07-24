# P0 Keyword Retrieval Smoke Test

## Scope and safety boundary

This record covers the first local qmd collection for the 11 manually approved
Milianke P0 documents. The source files remain in the private workspace and are
not copied into the repository. The collection is a `raw` collection and was
indexed with qmd 1.0.9's local full-text BM25 path only.

No `qmd embed`, `qmd query`, `qmd vsearch`, cloud MinerU provider, API key,
embedding model, reranker model, Wiki snapshot, or Gitee repository was used.

## Collection and processing result

- qmd version: `1.0.9`
- collection: `milianke-dr1-p0`
- source directory: `/home/dministrator/vendor/anlogic-dr1-knowledge/milianke/p0`
- collection pattern: `**/*.pdf`
- collection type: `raw`
- collection description/context: `米联客 MLK-F3P-CZ02-DR1M90G 的首批板卡启动、Linux、Buildroot、SDK、FPSoC 和 NPU 参考资料，仅包含人工批准的 P0 文档。`
- collection command:

  ```bash
  /home/dministrator/bin/qmd-dr1 collection add \
    /home/dministrator/vendor/anlogic-dr1-knowledge/milianke/p0 \
    --name milianke-dr1-p0 \
    --mask '**/*.pdf'
  ```

- collection-root context command (qmd has no separate description option):

  ```bash
  /home/dministrator/bin/qmd-dr1 context add \
    qmd://milianke-dr1-p0/ \
    '米联客 MLK-F3P-CZ02-DR1M90G 的首批板卡启动、Linux、Buildroot、SDK、FPSoC 和 NPU 参考资料，仅包含人工批准的 P0 文档。'
  ```

- source files discovered: `11`
- successfully indexed: `11`
- failed documents: `0`
- qmd status after indexing: `11 files indexed`, `0 embedded vectors`, `11 pending embedding`
- vectors: `0`
- full command log: `/home/dministrator/vendor/anlogic-dr1-knowledge/logs/p0_collection.log`

The qmd `ls` output showed one indexed entry for each approved source. Its
display paths are normalized collection-relative paths (lower-cased and with
punctuation normalized); the source SHA256 identity remains governed by
`.knowledge/manifests/p0_documents.yaml`.

## Keyword smoke queries

All commands below use BM25 keyword search and were run against only
`milianke-dr1-p0`:

```bash
/home/dministrator/bin/qmd-dr1 search 'PuTTY' -c milianke-dr1-p0 --line-numbers -n 5
/home/dministrator/bin/qmd-dr1 search 'root' -c milianke-dr1-p0 --line-numbers -n 5
/home/dministrator/bin/qmd-dr1 search '115200' -c milianke-dr1-p0 --line-numbers -n 5
/home/dministrator/bin/qmd-dr1 search '出厂' -c milianke-dr1-p0 --line-numbers -n 5
/home/dministrator/bin/qmd-dr1 search '二次开发' -c milianke-dr1-p0 --line-numbers -n 5
/home/dministrator/bin/qmd-dr1 search 'rootfs' -c milianke-dr1-p0 --line-numbers -n 5
/home/dministrator/bin/qmd-dr1 search 'DDR EMMC' -c milianke-dr1-p0 --line-numbers -n 5
/home/dministrator/bin/qmd-dr1 search 'CPU' -c milianke-dr1-p0 --line-numbers -n 5
/home/dministrator/bin/qmd-dr1 search '参考设计' -c milianke-dr1-p0 --line-numbers -n 5
/home/dministrator/bin/qmd-dr1 search 'Video' -c milianke-dr1-p0 --line-numbers -n 5
/home/dministrator/bin/qmd-dr1 search '工程' -c milianke-dr1-p0 --line-numbers -n 5
/home/dministrator/bin/qmd-dr1 search 'SDK' -c milianke-dr1-p0 --line-numbers -n 5
/home/dministrator/bin/qmd-dr1 search '交叉' -c milianke-dr1-p0 --line-numbers -n 5
```

The following table records the real hit paths and short snippets. Line
numbers are qmd's extracted-text addresses; they are not asserted PDF page
numbers.

| Item | Query and hit | Relevant snippet / location | Assessment |
| --- | --- | --- | --- |
| Serial login, baud, user, password | `PuTTY`; `root`; `115200` | `linux/.../putty安装与使用.pdf` lines 3–6 identify PuTTY; `linux/.../Linux出厂系统测试.pdf` lines 147–149 show `root` as username and password; SDK lines 3369–3371 list `115200` among UART baud rates. | Relevant for locating the serial/login material. The 115200 hit is a general UART passage, not proof of the board-login setting. |
| Linux factory system test | `出厂` → `linux/.../Linux出厂系统测试.pdf` lines 3–6 | “Linux 出厂系统测试”; “Linux 开机测试-Linux 出厂系统测试”. | Directly relevant; title and opening section are locatable by extracted lines. |
| Buildroot secondary development and image generation | `二次开发`; `rootfs` → `linux/.../二次开发Buildroot篇.pdf` lines 3–6 and 130–131 | “Linux 开机测试-二次开发”; `make_rootfs.sh`. A Linux-basics hit at lines 312–314 mentions rootfs, boot.bin and SD-card burning. | Directly relevant for locating Buildroot/rootfs material. The English `Buildroot` token alone and an over-constrained multi-term query returned no results, so Chinese/file-specific keywords are more reliable. |
| DR1 CPU, DDR, eMMC, system architecture | `DDR EMMC`; `CPU` → board manuals lines 106–114, UG1214 lines 160–163, SDK lines 588–591 | Board text names DDR3/eMMC; UG1214 TOC names the CPU chapter; SDK describes PS DDR, FLASH, EMMC, TF-Card, UART, USB and Ethernet. | Relevant cross-document navigation; the results do not by themselves freeze a board revision or runtime environment. |
| NPU reference design | `参考设计` → `hardware/apug1205-npu参考设计文档.pdf` lines 14–17 | “NPU 参考设计文档”. | Direct hit on the intended P0 document. |
| Video NPU IP | `Video` → `hardware/ipug166-video-npu-ip用户手册.pdf` lines 13–15; APUG1205 lines 351–354 | “Video NPU IP 用户手册”; “Video NPU IP 可通过IP Catalog 生成”. | Relevant hits; the APUG1205 result is a related cross-reference, not a duplicate. |
| FPSoC SDK project/toolchain | `工程`; `SDK` → FPSoC application guide lines 62–65; SDK guide lines 65–67 and 490–493; Buildroot guide lines 105–108 | “新建TD 工程”; “搭建SoC 系统工程”; `soc_prj`; `soc_fsbl.elf`, `system.bit`; SDK introduction. | Directly locatable project/toolchain passages. A separate `交叉` probe also located the Linux-basics cross-compilation chapter at lines 105–107. |

## Retrieval quality notes

- All 11 approved PDFs were processed without an indexing failure.
- Chinese and English text, document titles, and line-addressed snippets were
  returned for the tested topics.
- The extracted text contains minor layout/OCR artifacts, including blank
  lines, symbol glyphs such as ``/`` in some vendor pages, and escaped path
  text such as `\\soc_sdk\\`. These did not prevent the tested hits from being
  located, but the snippets are not a substitute for PDF visual review.
- qmd search exposes extracted line addresses and titles, but did not expose a
  reliable PDF `page:N` address for this collection. A probe of
  `qmd doc-toc` for the factory-test PDF returned an empty `sections` list.
  Printed page numbers sometimes appear inside table-of-contents text, but
  page mapping is therefore `not established` by this smoke test.
- No query produced duplicate copies of the same collection-relative path.
  Multiple hits for Video/CPU/DDR are expected cross-document matches. The
  manifest and copied-file SHA256 checks remain the authority for exact
  identity and duplicate status.
- Basic keyword lookup is usable without vectors. Vector search is not needed
  for this smoke test. It could improve synonym-heavy or over-constrained
  natural-language queries, but enabling it would require the prohibited
  embedding stage and model download; no such recommendation is made now.

## Manifest state

The 11 successfully indexed records in
`.knowledge/manifests/p0_documents.yaml` now have
`index_status: keyword_indexed`. No unapproved record was indexed or changed;
the remaining records stay `not_indexed`. All records retain their existing
`approved_for_copy` and priority values.

## Next-step boundary

Do **not** run `qmd embed` for this task. The collection currently has
`vectors: 0`, and the local keyword smoke test is complete. Any later vector
indexing decision requires a separately approved task and explicit model,
storage, and provenance review.
