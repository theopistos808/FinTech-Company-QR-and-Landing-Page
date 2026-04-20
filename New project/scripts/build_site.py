#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".vendor"))

import fitz
import qrcode
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = Path("/Users/jaycinasser/Downloads/Company One Pagers.pdf")
DATA_DIR = ROOT / "data"
ASSET_DIR = ROOT / "assets" / "companies"
JPG_DIR = ASSET_DIR / "jpg"
QR_DIR = ASSET_DIR / "qr"
PDF_DIR = ASSET_DIR / "pdf"
COMPANY_DIR = ROOT / "companies"


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return slug or "company"


def first_meaningful_line(lines: list[str]) -> str:
    for line in lines:
        clean = " ".join(line.split()).strip()
        if not clean:
            continue
        if len(clean) < 2:
            continue
        return clean
    return "Untitled Company"


def extract_section(lines: list[str], heading: str) -> str:
    try:
        index = lines.index(heading)
    except ValueError:
        return ""

    collected: list[str] = []
    for line in lines[index + 1 :]:
        candidate = line.strip()
        if not candidate:
            continue
        if candidate.isupper() and len(candidate) > 4:
            break
        if candidate.startswith("Company Executive Briefing"):
            break
        collected.append(candidate)
        if len(" ".join(collected)) > 220:
            break
    return " ".join(collected).strip()


def unique_slug(base_slug: str, seen: set[str]) -> str:
    if base_slug not in seen:
        seen.add(base_slug)
        return base_slug

    counter = 2
    while f"{base_slug}-{counter}" in seen:
        counter += 1
    slug = f"{base_slug}-{counter}"
    seen.add(slug)
    return slug


def reset_output_dirs() -> None:
    for directory in [JPG_DIR, QR_DIR, PDF_DIR, COMPANY_DIR]:
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def render_jpg(page: fitz.Page, destination: Path) -> None:
    pix = page.get_pixmap(matrix=fitz.Matrix(2.4, 2.4), alpha=False)
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    image.save(destination, "JPEG", quality=92, optimize=True)


def save_single_page_pdf(document: fitz.Document, page_index: int, destination: Path) -> None:
    single = fitz.open()
    single.insert_pdf(document, from_page=page_index, to_page=page_index)
    single.save(destination)
    single.close()


def save_qr(url: str, destination: Path) -> None:
    qr = qrcode.QRCode(border=2, box_size=8)
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    image.save(destination)


def write_company_page(company: dict[str, Any]) -> None:
    company_path = COMPANY_DIR / company["slug"]
    company_path.mkdir(parents=True, exist_ok=True)

    title = html.escape(company["title"])
    location = html.escape(company["location"])
    overview = html.escape(company["overview"])
    url = html.escape(company["url"])
    image_path = html.escape(company["image_path"])
    qr_path = html.escape(company["qr_path"])
    pdf_path = html.escape(company["pdf_path"])
    page_label = html.escape(str(company["page_number"]))

    page_html = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title} | Where is FinTech Changing Lives</title>
    <meta name="description" content="{title} from FinTech @ IU." />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700;800&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="/assets/site.css" />
  </head>
  <body class="detail-body">
    <main class="detail-shell">
      <a class="detail-back" href="/">Back to all companies</a>
      <section class="detail-hero">
        <div>
          <p class="eyebrow">FinTech @ IU</p>
          <h1>{title}</h1>
          <p class="detail-location">{location}</p>
          <p class="detail-copy">{overview}</p>
          <div class="detail-actions">
            <a class="button button-dark" href="{pdf_path}" target="_blank" rel="noreferrer">Open PDF page</a>
            <a class="button button-light" href="{url}" target="_blank" rel="noreferrer">Visit public URL</a>
          </div>
        </div>
        <aside class="qr-panel">
          <img src="{qr_path}" alt="QR code for {title}" />
          <p>Scan to open this page</p>
          <span>Page {page_label}</span>
        </aside>
      </section>
      <section class="detail-image-wrap">
        <img class="detail-image" src="{image_path}" alt="{title} one pager" />
      </section>
    </main>
  </body>
</html>
"""

    (company_path / "index.html").write_text(page_html, encoding="utf-8")


def build(pdf_path: Path, base_url: str) -> list[dict[str, Any]]:
    reset_output_dirs()
    base_url = base_url.rstrip("/")
    document = fitz.open(pdf_path)
    seen_slugs: set[str] = set()
    companies: list[dict[str, Any]] = []

    for page_index in range(document.page_count):
        page = document.load_page(page_index)
        lines = [line.strip() for line in page.get_text("text").splitlines() if line.strip()]
        title = first_meaningful_line(lines)
        slug = unique_slug(slugify(title), seen_slugs)
        location = lines[1] if len(lines) > 1 else ""
        overview = extract_section(lines, "OVERVIEW")
        detail_url = f"{base_url}/companies/{slug}/"

        jpg_path = JPG_DIR / f"{slug}.jpg"
        qr_path = QR_DIR / f"{slug}.png"
        pdf_output_path = PDF_DIR / f"{slug}.pdf"

        render_jpg(page, jpg_path)
        save_qr(detail_url, qr_path)
        save_single_page_pdf(document, page_index, pdf_output_path)

        company = {
            "title": title,
            "slug": slug,
            "location": location,
            "overview": overview,
            "page_number": page_index + 1,
            "url": detail_url,
            "image_path": f"/assets/companies/jpg/{slug}.jpg",
            "qr_path": f"/assets/companies/qr/{slug}.png",
            "pdf_path": f"/assets/companies/pdf/{slug}.pdf",
        }
        companies.append(company)
        write_company_page(company)

    document.close()

    payload = {"base_url": base_url, "companies": companies}
    (DATA_DIR / "companies.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return companies


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate company assets and static pages from a PDF.")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF, help="Path to the source PDF.")
    parser.add_argument(
        "--base-url",
        default="https://your-vercel-project.vercel.app",
        help="Public site base URL for QR codes.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.pdf.exists():
        print(f"PDF not found: {args.pdf}", file=sys.stderr)
        return 1

    companies = build(args.pdf, args.base_url)
    print(f"Generated {len(companies)} company pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
