#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render PDF pages to PNG files and rebuild an image-only PDF.

The renderer is PDFium (the engine used by Chromium), which handles embedded
and subset fonts more reliably than many system PDF renderers.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path

try:
    import pypdfium2 as pdfium
except ImportError:
    sys.exit("缺少依赖 pypdfium2，请执行: pip install -r requirements.txt")

try:
    from PIL import Image
except ImportError:
    sys.exit("缺少依赖 pillow，请执行: pip install -r requirements.txt")


def pngs_to_pdf(image_paths: list[Path], output_pdf: Path, dpi: int) -> None:
    """Write PNG pages to an image-only PDF in the supplied order."""
    if not image_paths:
        raise ValueError("没有可写入 PDF 的图片")
    try:
        with ExitStack() as stack:
            images = [
                stack.enter_context(Image.open(image_path)).convert("RGB")
                for image_path in image_paths
            ]
            first, *remaining = images
            first.save(
                output_pdf,
                format="PDF",
                save_all=True,
                append_images=remaining,
                resolution=dpi,
            )
    except Exception:
        output_pdf.unlink(missing_ok=True)
        raise


def merge_append_pdf(base_pdf: Path, append_pdf: Path) -> None:
    """Append every page of append_pdf to the end of base_pdf, in place."""
    merged = pdfium.PdfDocument.new()
    base = pdfium.PdfDocument(str(base_pdf))
    extra = pdfium.PdfDocument(str(append_pdf))
    try:
        merged.import_pages(base)
        merged.import_pages(extra)
        temp_pdf = base_pdf.with_name(base_pdf.stem + "_tmp.pdf")
        merged.save(str(temp_pdf))
    finally:
        base.close()
        extra.close()
        merged.close()
    temp_pdf.replace(base_pdf)


def load_config(config_path: Path) -> dict:
    """Load and validate the JSON configuration."""
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"配置文件不存在: {config_path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"配置文件格式错误（第 {exc.lineno} 行）: {exc.msg}") from None

    defaults = {
        "input_dir": "input",
        "input_pdf": "",
        "images_dir": "output/images",
        "merged_pdf_dir": "output/merged_pdfs",
        "dpi": 300,
        "save_images": True,
        "merge_pdf": True,
        "append_pdf": "",
        "append_pdf_enabled": False,
    }
    defaults.update(config)
    if not isinstance(defaults["input_pdf"], str):
        raise ValueError("配置项 input_pdf 必须是字符串")
    if not isinstance(defaults["dpi"], int) or defaults["dpi"] <= 0:
        raise ValueError("配置项 dpi 必须是大于 0 的整数")
    for key in ("save_images", "merge_pdf", "append_pdf_enabled"):
        if not isinstance(defaults[key], bool):
            raise ValueError(f"配置项 {key} 必须是 true 或 false")
    if not isinstance(defaults["append_pdf"], str):
        raise ValueError("配置项 append_pdf 必须是字符串")
    if not defaults["save_images"] and not defaults["merge_pdf"]:
        raise ValueError("save_images 和 merge_pdf 不能同时为 false")
    if defaults["append_pdf_enabled"] and not defaults["append_pdf"].strip():
        raise ValueError("append_pdf_enabled 为 true 时必须指定 append_pdf")
    return defaults


def resolve_append_pdf(config: dict) -> Path | None:
    """Resolve the PDF that gets appended, or None when appending is off."""
    if not config["append_pdf_enabled"]:
        return None
    name = config["append_pdf"].strip()
    if not name:
        return None
    append_pdf = Path(name).expanduser()
    if not append_pdf.is_absolute():
        append_pdf = Path(config["input_dir"]) / append_pdf
    if not append_pdf.is_file():
        raise ValueError(f"指定的追加 PDF 不存在: {append_pdf}")
    if append_pdf.suffix.lower() != ".pdf":
        raise ValueError(f"append_pdf 指定的不是 PDF 文件: {append_pdf}")
    return append_pdf


def convert(pdf_path: Path, config: dict, append_pdf: Path | None = None) -> bool:
    """Convert one PDF according to config."""
    try:
        document = pdfium.PdfDocument(str(pdf_path))
    except Exception as exc:
        print(f"[跳过] 无法打开 {pdf_path}: {exc}", file=sys.stderr)
        return False

    try:
        page_count = len(document)
        if page_count == 0:
            print(f"[跳过] PDF 没有页面: {pdf_path}", file=sys.stderr)
            return False

        dpi = config["dpi"]
        save_images = config["save_images"]
        merge_pdf = config["merge_pdf"]
        permanent_images_dir = (
            Path(config["images_dir"]) / pdf_path.stem / f"{dpi}dpi"
        )
        temp_context = None
        if save_images:
            render_dir = permanent_images_dir
            render_dir.mkdir(parents=True, exist_ok=True)
        else:
            temp_context = tempfile.TemporaryDirectory(prefix="pdf2img_")
            render_dir = Path(temp_context.name)

        try:
            image_paths: list[Path] = []
            for index in range(page_count):
                page = document[index]
                bitmap = page.render(scale=dpi / 72.0)
                image = bitmap.to_pil().convert("RGB")
                image_path = render_dir / f"page_{index + 1:04d}.png"
                image.save(image_path, format="PNG", dpi=(dpi, dpi))
                image_paths.append(image_path)
                if save_images:
                    print(f"[图片] {image_path} ({image.width}x{image.height})")
                image.close()
                bitmap.close()
                page.close()

            if merge_pdf:
                pdf_dir = Path(config["merged_pdf_dir"]) / pdf_path.stem
                pdf_dir.mkdir(parents=True, exist_ok=True)
                output_pdf = pdf_dir / f"{pdf_path.stem}_image_{dpi}dpi.pdf"
                pngs_to_pdf(image_paths, output_pdf, dpi)
                if append_pdf is not None:
                    merge_append_pdf(output_pdf, append_pdf)
                    print(f"[追加] {append_pdf} 已合并到 {output_pdf}")
                print(f"[PDF]  {output_pdf}")
        finally:
            if temp_context is not None:
                temp_context.cleanup()
    finally:
        document.close()
    return True


def discover_inputs(raw_paths: list[str], input_dir: Path) -> list[Path]:
    """Resolve explicit paths/globs, or all PDFs under input_dir."""
    if not raw_paths:
        input_dir.mkdir(parents=True, exist_ok=True)
        return sorted(input_dir.glob("*.pdf"))

    resolved: list[Path] = []
    for raw in raw_paths:
        candidate = Path(raw).expanduser()
        if candidate.is_file():
            resolved.append(candidate)
            continue
        parent = candidate.parent
        matches = sorted(parent.glob(candidate.name)) if parent.exists() else []
        resolved.extend(path for path in matches if path.is_file())
        if not matches:
            print(f"[跳过] 文件不存在: {candidate}", file=sys.stderr)
    return resolved


def configured_input(config: dict) -> list[Path]:
    """Resolve the single PDF selected by config."""
    input_dir = Path(config["input_dir"])
    input_dir.mkdir(parents=True, exist_ok=True)
    configured_name = config["input_pdf"].strip()
    if configured_name:
        selected = Path(configured_name).expanduser()
        if not selected.is_absolute():
            selected = input_dir / selected
        if not selected.is_file():
            raise ValueError(f"指定的 PDF 不存在: {selected}")
        if selected.suffix.lower() != ".pdf":
            raise ValueError(f"input_pdf 指定的不是 PDF 文件: {selected}")
        return [selected]

    pdfs = sorted(input_dir.glob("*.pdf"))
    if not pdfs:
        raise ValueError(f"{input_dir} 目录中没有 PDF")
    if len(pdfs) > 1:
        names = "、".join(path.name for path in pdfs)
        raise ValueError(
            f"{input_dir} 中有多个 PDF，请在 config.json 的 input_pdf 中指定一个：{names}"
        )
    return pdfs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="使用 PDFium 将 PDF 转为 PNG，并按原顺序生成图片版 PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python pdf2img.py 文件.pdf\n"
            "  python pdf2img.py                 # 按 config.json 批量处理"
        ),
    )
    parser.add_argument("pdfs", nargs="*", help="PDF 路径，可传多个或使用通配符")
    parser.add_argument(
        "-c", "--config", default="config.json", help="配置文件，默认 ./config.json"
    )
    args = parser.parse_args()

    try:
        config = load_config(Path(args.config))
    except ValueError as exc:
        print(f"[配置错误] {exc}", file=sys.stderr)
        return 2

    if args.pdfs:
        pdf_paths = discover_inputs(args.pdfs, Path(config["input_dir"]))
        if not pdf_paths:
            print("未找到指定的 PDF。", file=sys.stderr)
            return 1
    else:
        try:
            pdf_paths = configured_input(config)
        except ValueError as exc:
            print(f"[输入错误] {exc}", file=sys.stderr)
            return 1

    try:
        append_pdf = resolve_append_pdf(config)
    except ValueError as exc:
        print(f"[配置错误] {exc}", file=sys.stderr)
        return 2

    completed = 0
    for pdf_path in pdf_paths:
        if convert(pdf_path, config, append_pdf):
            completed += 1

    if not completed:
        return 1
    print(f"\n全部完成：处理 {completed} 个 PDF。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
