#!/usr/bin/env python3
"""Read-only newspaper optical-disc scanner and lossless whole-issue PDF exporter."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import re
from collections import Counter
from pathlib import Path

import img2pdf
import pikepdf
from PIL import Image, ImageStat
from pypdf import PdfReader


PAPER_NAME = "国民日报"
SEP = "＊"
ENCODING = "utf-8-sig"
EMPTY_JPEG_PREFIX = b"\xff\xd8\xff\xd9"


def safe_name(value: str) -> str:
    cleaned = "".join(ch for ch in value if ch not in '<>:"/\\|?*').strip()
    return cleaned or "光盘"


def locate_source(drive: Path, override: str | None) -> Path:
    if override:
        source = Path(override)
        if source.is_dir():
            return source
        raise RuntimeError(f"指定的图片目录不可访问：{source}")
    known = drive / "019Z" / (chr(127) * 8) / "pic"
    if known.is_dir():
        return known
    candidates: list[Path] = []
    for year in drive.rglob("*"):
        if year.is_dir() and re.fullmatch(r"\d{4}", year.name) and year.parent.name.lower() == "pic":
            candidates.append(year.parent)
    unique = list(dict.fromkeys(candidates))
    if len(unique) == 1:
        return unique[0]
    raise RuntimeError(f"无法唯一定位 pic 日期目录，候选数={len(unique)}；保持只读并先分析光盘格式")


def discover(source: Path, sample_date: str | None = None) -> list[tuple[str, list[tuple[int, Path]]]]:
    result: list[tuple[str, list[tuple[int, Path]]]] = []
    years = sorted((p for p in source.iterdir() if p.is_dir() and p.name.isdigit()), key=lambda p: int(p.name))
    for year in years:
        months = sorted((p for p in year.iterdir() if p.is_dir() and p.name.isdigit()), key=lambda p: int(p.name))
        for month in months:
            days = sorted((p for p in month.iterdir() if p.is_dir() and p.name.isdigit()), key=lambda p: int(p.name))
            for day in days:
                date = f"{int(year.name):04d}-{int(month.name):02d}-{int(day.name):02d}"
                if sample_date and date != sample_date:
                    continue
                pages = [(int(path.stem), path) for path in day.glob("*.jpg") if path.stem.isdigit()]
                pages.sort(key=lambda item: item[0])
                if pages:
                    result.append((date, pages))
    return result


def calendar_gaps(values: list[str]) -> list[str]:
    parsed = sorted(dt.date.fromisoformat(value) for value in values)
    if not parsed:
        return []
    present = set(parsed)
    current = parsed[0]
    gaps = []
    while current <= parsed[-1]:
        if current not in present:
            gaps.append(current.isoformat())
        current += dt.timedelta(days=1)
    return gaps


def missing_editions(pages: list[tuple[int, Path]]) -> list[int]:
    actual = [edition for edition, _ in pages]
    return sorted(set(range(1, max(actual) + 1)) - set(actual))


def safe_jpeg_bytes(data: bytes) -> tuple[bytes, int]:
    if data.startswith(EMPTY_JPEG_PREFIX + b"\xff\xd8"):
        return data[len(EMPTY_JPEG_PREFIX):], len(EMPTY_JPEG_PREFIX)
    return data, 0


def inspect_header(path: Path) -> dict:
    try:
        with Image.open(path) as image:
            return {"width": image.width, "height": image.height, "format": image.format or "", "mode": image.mode, "error": ""}
    except Exception as exc:
        return {"width": 0, "height": 0, "format": "", "mode": "", "error": repr(exc)}


def inspect_image(data: bytes) -> dict:
    result = {"width": 0, "height": 0, "format": "", "mode": "", "dpi_x": "", "dpi_y": "",
              "white_black": "", "error": ""}
    try:
        with Image.open(io.BytesIO(data)) as image:
            result["width"], result["height"] = image.size
            result["format"] = image.format or ""
            result["mode"] = image.mode
            dpi = image.info.get("dpi", ("", ""))
            if isinstance(dpi, tuple) and len(dpi) >= 2:
                result["dpi_x"] = round(float(dpi[0]), 2)
                result["dpi_y"] = round(float(dpi[1]), 2)
            sample = image.convert("L")
            sample.thumbnail((128, 128))
            stat = ImageStat.Stat(sample)
            mean, std = float(stat.mean[0]), float(stat.stddev[0])
            if std < 2 and mean >= 250:
                result["white_black"] = "疑似纯白"
            elif std < 2 and mean <= 5:
                result["white_black"] = "疑似纯黑"
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def expected_path(output_root: Path, date: str, page_count: int) -> Path:
    year, month, _ = date.split("-")
    return output_root / year / f"{year}-{month}" / f"{PAPER_NAME}{SEP}{date}{SEP}共{page_count:02d}版.pdf"


def verify_pdf(path: Path, expected_hashes: list[bytes]) -> tuple[bool, int, str]:
    try:
        page_count = len(PdfReader(str(path), strict=False).pages)
        if page_count != len(expected_hashes):
            return False, page_count, f"页数错误：期望 {len(expected_hashes)}，实际 {page_count}"
        pdf = pikepdf.Pdf.open(path)
        try:
            for index, (page, expected_hash) in enumerate(zip(pdf.pages, expected_hashes), start=1):
                images = [obj for obj in page.Resources.get("/XObject", {}).values()
                          if obj.get("/Subtype") == pikepdf.Name.Image and obj.get("/Filter") == pikepdf.Name.DCTDecode]
                if len(images) != 1:
                    return False, page_count, f"第{index:02d}页 DCT 图像数={len(images)}"
                if hashlib.sha256(images[0].read_raw_bytes()).digest() != expected_hash:
                    return False, page_count, f"第{index:02d}页内嵌 JPEG 与对应版次原图不一致"
        finally:
            pdf.close()
        return True, page_count, ""
    except Exception as exc:
        return False, 0, repr(exc)


def create_or_verify(streams: list[bytes], destination: Path) -> tuple[str, int, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    alternatives = [path for path in destination.parent.glob(f"{PAPER_NAME}{SEP}{destination.name.split(SEP)[1]}{SEP}共*版.pdf")
                    if path != destination]
    if alternatives and not destination.exists():
        return "冲突未覆盖", 0, "同日期已存在其他整期 PDF：" + "; ".join(str(path) for path in alternatives)
    expected_hashes = [hashlib.sha256(data).digest() for data in streams]
    if destination.exists():
        ok, count, error = verify_pdf(destination, expected_hashes)
        if ok:
            return "已验证跳过", count, ""
        return "冲突未覆盖", count, f"现有文件校验失败：{error}"
    partial = destination.with_name(destination.name + ".partial")
    if partial.exists():
        partial.unlink()
    pdf_bytes = img2pdf.convert([io.BytesIO(data) for data in streams], rotation=img2pdf.Rotation.ifvalid)
    try:
        with partial.open("xb") as handle:
            handle.write(pdf_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        ok, count, error = verify_pdf(partial, expected_hashes)
        if not ok:
            raise IOError(error)
        os.replace(partial, destination)
        return "生成成功", count, ""
    except Exception:
        if partial.exists():
            partial.unlink()
        raise


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=ENCODING, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def preflight(dates: list[tuple[str, list[tuple[int, Path]]]], output_root: Path, source: Path,
              drive: Path, disc_name: str, disc_label: str) -> dict:
    dimensions = Counter()
    orientations = Counter()
    header_errors = []
    overlaps = []
    edition_anomalies = []
    for date, pages in dates:
        missing = missing_editions(pages)
        if missing:
            edition_anomalies.append({"date": date, "missing": missing})
        month_dir = expected_path(output_root, date, len(pages)).parent
        existing = list(month_dir.glob(f"{PAPER_NAME}{SEP}{date}{SEP}共*版.pdf")) if month_dir.exists() else []
        if existing:
            overlaps.append({"date": date, "files": [str(path) for path in existing]})
        for edition, image in pages:
            info = inspect_header(image)
            dimensions[f"{info['width']}x{info['height']}"] += 1
            orientations["landscape" if info["width"] > info["height"] else "portrait"] += 1
            if info["error"]:
                header_errors.append({"date": date, "edition": edition, "path": str(image), "error": info["error"]})
    date_values = [date for date, _ in dates]
    return {
        "disc_name": disc_name,
        "disc_label": disc_label,
        "drive": str(drive),
        "source": str(source),
        "date_start": date_values[0],
        "date_end": date_values[-1],
        "date_count": len(dates),
        "page_count": sum(len(pages) for _, pages in dates),
        "page_count_distribution": dict(Counter(len(pages) for _, pages in dates)),
        "calendar_gaps": calendar_gaps(date_values),
        "edition_anomalies": edition_anomalies,
        "existing_date_overlaps": overlaps,
        "dimensions": dict(dimensions),
        "orientations": dict(orientations),
        "header_errors": header_errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--drive", default="F:\\")
    parser.add_argument("--disc-name", required=True)
    parser.add_argument("--disc-label", default="")
    parser.add_argument("--source-root")
    parser.add_argument("--sample-date")
    parser.add_argument("--scan-only", action="store_true")
    args = parser.parse_args()

    project = Path(args.project_root).resolve()
    drive = Path(args.drive)
    if not drive.is_dir():
        raise RuntimeError(f"光盘路径不可访问：{drive}")
    disc_name = safe_name(args.disc_name)
    disc_label = args.disc_label.strip() or disc_name
    output_root = project / "output" / "01_整期PDF"
    reports = project / "output" / "99_目录与报告"
    reports.mkdir(parents=True, exist_ok=True)
    source = locate_source(drive, args.source_root)
    all_dates = discover(source)
    if not all_dates:
        raise RuntimeError("没有发现 YYYY/MM/DD/NN.jpg 报纸图片")

    scan_path = reports / f"{disc_name}扫描结果.json"
    quick_identity = {
        "disc_label": disc_label,
        "source": str(source),
        "date_start": all_dates[0][0],
        "date_end": all_dates[-1][0],
        "date_count": len(all_dates),
        "page_count": sum(len(pages) for _, pages in all_dates),
    }
    scan = None
    if not args.scan_only and scan_path.exists():
        try:
            cached = json.loads(scan_path.read_text(encoding="utf-8"))
            if all(cached.get(key) == value for key, value in quick_identity.items()):
                scan = cached
                print(f"REUSE_SCAN {scan_path}", flush=True)
        except Exception:
            scan = None
    if scan is None:
        scan = preflight(all_dates, output_root, source, drive, disc_name, disc_label)
        scan_path.write_text(json.dumps(scan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(scan, ensure_ascii=False, indent=2), flush=True)
    if args.scan_only:
        return 2 if scan["header_errors"] or scan["edition_anomalies"] else 0

    dates = discover(source, args.sample_date)
    if not dates:
        raise RuntimeError(f"样本日期不存在：{args.sample_date}")
    suffix = f"_{args.sample_date}" if args.sample_date else ""
    rows = []
    failures = []
    dimensions = Counter()
    orientations = Counter()
    formats = Counter()
    modes = Counter()
    source_bytes = 0
    prefix_bytes = 0
    image_errors = 0
    white_black = 0
    for date_index, (date, pages) in enumerate(dates, start=1):
        missing = missing_editions(pages)
        prepared = []
        problems = []
        date_prefix = 0
        for edition, path in pages:
            raw = path.read_bytes()
            source_bytes += len(raw)
            data, removed = safe_jpeg_bytes(raw)
            prepared.append(data)
            date_prefix += removed
            info = inspect_image(raw)
            dimensions[f"{info['width']}x{info['height']}"] += 1
            orientations["横向" if info["width"] > info["height"] else "纵向"] += 1
            formats[info["format"]] += 1
            modes[info["mode"]] += 1
            if info["error"]:
                image_errors += 1
                problems.append(f"第{edition:02d}版损坏：{info['error']}")
            if info["white_black"]:
                white_black += 1
                problems.append(f"第{edition:02d}版{info['white_black']}")
        destination = expected_path(output_root, date, len(pages))
        status, pdf_pages, error = "未生成", 0, ""
        if missing:
            error = "缺版：" + ",".join(f"{value:02d}" for value in missing)
        elif problems:
            error = "; ".join(problems)
        else:
            try:
                status, pdf_pages, error = create_or_verify(prepared, destination)
                if status == "生成成功":
                    prefix_bytes += date_prefix
            except Exception as exc:
                status, error = "失败", repr(exc)
        ok = status in {"生成成功", "已验证跳过"} and pdf_pages == len(pages) and not error
        if not ok:
            failures.append({"日期": date, "阶段": "整期PDF", "目标文件": str(destination), "错误": error or status})
        editions = [edition for edition, _ in pages]
        rows.append({"光盘标签": disc_label, "日期": date, "版数": len(pages), "最小版次": min(editions),
                     "最大版次": max(editions), "缺版": ",".join(f"{value:02d}" for value in missing),
                     "来源目录": str(pages[0][1].parent), "整期PDF": str(destination), "PDF页数": pdf_pages,
                     "状态": "成功" if ok else "异常", "处理动作": status, "备注": error})
        print(f"[{date_index}/{len(dates)}] {date} 版数={len(pages)} PDF页数={pdf_pages} 状态={'成功' if ok else '异常'}", flush=True)

    fields = ["光盘标签", "日期", "版数", "最小版次", "最大版次", "缺版", "来源目录", "整期PDF", "PDF页数", "状态", "处理动作", "备注"]
    write_csv(reports / f"{disc_name}整期PDF清单{suffix}.csv", rows, fields)
    write_csv(reports / f"{disc_name}导出失败{suffix}.csv", failures, ["日期", "阶段", "目标文件", "错误"])

    if not args.sample_date:
        successful = sum(row["状态"] == "成功" for row in rows)
        gaps = calendar_gaps([row["日期"] for row in rows])
        report = f"""# {disc_name}导出报告

生成时间：{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 来源与范围

- 光盘路径：`{drive}`（只读）
- 光盘标签：`{disc_label}`
- 图片目录：`{source}`
- 日期范围：{rows[0]['日期']} 至 {rows[-1]['日期']}

## 结果

- 日期：{len(rows)}
- 版面：{sum(int(row['版数']) for row in rows):,}
- 成功整期 PDF：{successful}
- 失败：{len(failures)}
- 缺版日期：{sum(bool(row['缺版']) for row in rows)}
- 原始扫描数据量：{source_bytes / 1024**3:.2f} GiB
- 输出目录：`{output_root}`

## 质量

- 尺寸分布：{dict(dimensions)}
- 页面方向：{dict(orientations)}；保持原扫描方向，不旋转或拉伸。
- 图像格式：{dict(formats)}
- 图像模式：{dict(modes)}
- 损坏图片：{image_errors}
- 疑似纯白/纯黑页面：{white_black}
- PDF 均检查可打开性、页数、逐页内嵌 JPEG 码流和版次顺序。
- JPEG 未重新压缩；新生成 PDF 共无损去除 {prefix_bytes:,} 个空 JPEG 前缀字节。

## 来源缺档

- 日期范围内无目录：{', '.join(gaps) if gaps else '无'}
- 只记录来源缺档，不依据文件时间推测报纸日期。

Windows 文件名使用全角 `＊` 代替禁止使用的半角星号。
"""
        (reports / f"{disc_name}导出报告.md").write_text(report, encoding="utf-8")
    print(f"DONE dates={len(rows)} pages={sum(int(row['版数']) for row in rows)} failures={len(failures)}")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
