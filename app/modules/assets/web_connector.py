import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import httpx
from PIL import Image, ImageDraw

from .models import Asset, AssetContent


def is_xd_url(url: str) -> bool:
    return "xd.adobe.com" in url.lower()


def find_browser_executable() -> str | None:
    candidates = [
        shutil.which("chrome"),
        shutil.which("chrome.exe"),
        shutil.which("msedge"),
        shutil.which("msedge.exe"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def capture_headless_screenshot(url: str, target_path: Path, wait_ms: int = 8000,
                                width: int = 1920, height: int = 1080) -> bool:
    browser = find_browser_executable()
    if not browser:
        return False
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_user_data = tempfile.mkdtemp(prefix="audit_browser_")
    try:
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={tmp_user_data}",
            f"--window-size={width},{height}",
            f"--virtual-time-budget={wait_ms}",
            f"--screenshot={str(target_path.resolve())}",
            url
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return target_path.exists() and target_path.stat().st_size > 0
    except Exception:
        return False
    finally:
        shutil.rmtree(tmp_user_data, ignore_errors=True)


def _generate_web_card_preview(url: str, title: str, snippet: str, target_path: Path) -> str:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (800, 450), color=(245, 247, 250))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 780, 80], fill=(31, 42, 68))
    draw.text((40, 40), f"WEB ELÖNÉZET: {urlparse(url).netloc}", fill=(255, 255, 255))
    draw.rectangle([20, 100, 780, 430], fill=(255, 255, 255), outline=(220, 224, 230))
    draw.text((40, 120), f"Oldal címe: {title[:70]}", fill=(30, 41, 59))
    clean_snippet = re.sub(r"\s+", " ", snippet)[:300]
    draw.text((40, 160), f"Kinyert tartalom:\n{clean_snippet}", fill=(100, 116, 139))
    img.save(str(target_path), "PNG")
    return str(target_path)


def fetch_xd_content(url: str, prev_dir: str = "data/previews") -> tuple[str, str, list[dict], str]:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    title = "Adobe XD Terv"
    blocks: list[dict] = []
    text_pieces: list[str] = []

    try:
        resp = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
        if resp.status_code == 200:
            m = re.search(r"window\.prototypeData\s*=\s*(\{.*?\});\s*(?:if|window)", resp.text, re.DOTALL)
            if m:
                data = json.loads(m.group(1))
                manifest = data.get("manifest", {})
                title = manifest.get("name", title)
                for ab in manifest.get("artboards", []):
                    ab_name = ab.get("name", "")
                    if ab_name:
                        text_pieces.append(f"Artboard: {ab_name}")
                        blocks.append({"page": 0, "bbox": [0, 0, 100, 50], "text": ab_name, "origin": "xd_artboard"})
    except Exception:
        pass

    preview_target = Path(prev_dir) / f"xd_{abs(hash(url))}.png"
    captured = capture_headless_screenshot(url, preview_target, wait_ms=8000)
    preview_file = str(preview_target) if captured else _generate_web_card_preview(url, title, "\n".join(text_pieces), preview_target)

    plain_text = "\n".join(text_pieces) if text_pieces else f"{title}\nAdobe XD Prototipe Artboard"
    return title, plain_text, blocks, preview_file


def fetch_generic_web_content(url: str, prev_dir: str = "data/previews") -> tuple[str, str, list[dict], str]:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    resp = httpx.get(url, headers=headers, timeout=15.0, follow_redirects=True)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else urlparse(url).netloc
    preview_target = Path(prev_dir) / f"web_{abs(hash(url))}.png"

    blocks: list[dict] = []
    text_pieces: list[str] = []
    for idx, el in enumerate(soup.find_all(["h1", "h2", "h3", "h4", "p", "a", "button", "li"])):
        txt = el.get_text().strip()
        if txt and len(txt) > 2:
            text_pieces.append(txt)
            blocks.append({
                "page": 0, "bbox": [20, 20 + (idx * 30), 600, 45 + (idx * 30)],
                "text": txt, "origin": "web_dom"
            })

    plain_text = "\n".join(text_pieces)
    captured = capture_headless_screenshot(url, preview_target, wait_ms=4000)
    preview_file = str(preview_target) if captured else _generate_web_card_preview(url, title, plain_text, preview_target)
    return title, plain_text, blocks, preview_file


def fetch_web_content(url: str, prev_dir: str = "data/previews") -> tuple[str, str, list[dict], str]:
    if is_xd_url(url):
        return fetch_xd_content(url, prev_dir)
    return fetch_generic_web_content(url, prev_dir)


def ingest_url(db, campaign_id: int, url: str, name: str = "", prev_dir: str = "data/previews") -> Asset:
    title, plain_text, blocks, prev = fetch_web_content(url, prev_dir)
    ftype = "xd" if is_xd_url(url) else "web"
    asset = Asset(
        campaign_id=campaign_id, name=name or title or url,
        file_path=url, file_type=ftype, file_size=0, page_count=1,
        preview_path=prev
    )
    db.add(asset)
    db.flush()

    content = AssetContent(asset_id=asset.id, page_num=0, plain_text=plain_text, blocks=blocks)
    db.add(content)
    db.commit()
    return asset
