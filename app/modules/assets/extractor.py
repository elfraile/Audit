from pathlib import Path
import fitz
from PIL import Image


def _clean_text_lines(raw_lines: list[str]) -> list[str]:
    """Ismétlődő rétegek és üres sorok kiszűrése."""
    cleaned: list[str] = []
    for line in raw_lines:
        s = line.strip()
        if s and (not cleaned or cleaned[-1] != s):
            cleaned.append(s)
    return cleaned


def extract_pdf(pdf_path: str, preview_dir: str) -> tuple[int, str, list[dict], str]:
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    all_blocks: list[dict] = []
    text_lines: list[str] = []
    preview_file = ""

    if page_count > 0:
        first_page = doc[0]
        preview_name = f"prev_{Path(pdf_path).stem}.png"
        preview_target = Path(preview_dir) / preview_name
        preview_target.parent.mkdir(parents=True, exist_ok=True)
        pix = first_page.get_pixmap(dpi=150)
        pix.save(str(preview_target))
        preview_file = str(preview_target)

    for pno, page in enumerate(doc):
        raw_blocks = page.get_text("blocks")
        for b in raw_blocks:
            lines = _clean_text_lines(b[4].splitlines())
            if lines:
                block_text = "\n".join(lines)
                text_lines.extend(lines)
                all_blocks.append({
                    "page": pno,
                    "bbox": [round(coord, 1) for coord in b[:4]],
                    "text": block_text,
                    "origin": "vector_layer"
                })

    doc.close()
    plain_text = "\n".join(_clean_text_lines(text_lines))
    return page_count, plain_text, all_blocks, preview_file


def extract_image(img_path: str, preview_dir: str) -> tuple[int, str, list[dict], str]:
    preview_name = f"prev_{Path(img_path).stem}.png"
    preview_target = Path(preview_dir) / preview_name
    preview_target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(img_path) as img:
        img.thumbnail((1200, 1200))
        img.save(str(preview_target), "PNG")
    return 1, "", [], str(preview_target)
