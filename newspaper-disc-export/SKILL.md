---
name: newspaper-disc-export
description: Safely extract old Guomin Ribao newspaper CD/DVD collections into lossless whole-issue PDFs and per-disc export reports. Use when Codex is asked to process the next newspaper disc, inspect hidden 019Z/DEL-character data folders, continue chronological PDF output, avoid overwriting prior issues, or validate page counts and embedded JPEG order. Designed for read-only optical sources on Windows and output limited to 01_整期PDF plus 99_目录与报告.
---

# Newspaper Disc Export

Use the bundled deterministic scripts. Do not reimplement PDF generation unless the disc format differs.

## Non-negotiable rules

- Treat the optical drive as read-only. Never create, rename, modify, or delete anything on it.
- Never launch `autorun.exe` for the known disc family.
- Generate only whole-issue PDFs and this disc's reports unless the user explicitly expands scope.
- Preserve source dimensions, orientation, edges, DPI, grayscale, and JPEG compression data.
- Never rotate landscape scans merely to look upright. Preserve the recorded scan orientation.
- Never overwrite a successful PDF. Verify and skip it. Report an invalid or conflicting existing file.
- Sort dates and editions numerically.
- Do not infer newspaper dates from filesystem timestamps.

## Workflow

1. Resolve the optical drive and project root. Confirm the drive is accessible and record its volume label and filesystem with a read-only PowerShell check such as `Get-Volume -DriveLetter F`.
2. Resolve this skill's directory, then use `scripts/export_whole_pdf.py` from it.
3. If imports fail, run `scripts/setup.ps1 -ProjectRoot <project>` to create a project-local Python environment. Do not install system-wide packages.
4. Run a scan-only preflight first:

```powershell
& <python> <skill>\scripts\export_whole_pdf.py `
  --project-root 'D:\国民日报' --drive 'F:\' `
  --disc-name '第三张光盘' --disc-label 'gmrb3' --scan-only
```

5. Read the scan JSON under `output\99_目录与报告`. Check date range, edition continuity, calendar gaps, existing-date overlaps, image count, and source layout. Stop before export if a same-date collision exists and cannot be verified safely.
6. Export the earliest discovered date as a sample with `--sample-date YYYY-MM-DD`.
7. Render the sample PDF's first and last pages with Poppler. Also render one landscape page if the scan reports landscape images. Visually confirm content, ordering, borders, page proportions, and absence of white pages.
8. Run the same command without `--scan-only` or `--sample-date` for the full disc.
9. Confirm the command exits successfully, the failure CSV has no data rows, no `.partial` files remain, and the number of successful PDFs equals the discovered date count.
10. Open the Markdown report and summarize date range, PDF count, page count, missing dates/editions, image orientations, failures, and output location.

## Output contract

Write only to the project root:

```text
output/
├─ 01_整期PDF/
│  └─ YYYY/YYYY-MM/国民日报＊YYYY-MM-DD＊共XX版.pdf
└─ 99_目录与报告/
   ├─ <光盘名>扫描结果.json
   ├─ <光盘名>整期PDF清单.csv
   ├─ <光盘名>导出失败.csv
   └─ <光盘名>导出报告.md
```

Use fullwidth `＊` because Windows forbids `*` in filenames.

## Format-specific guidance

Read [references/disc-format.md](references/disc-format.md) when the known hidden directory is absent, images render blank, dimensions vary, or a collision must be diagnosed. Keep all discovery read-only.

