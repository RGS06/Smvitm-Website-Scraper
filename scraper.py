"""
Enhanced Universal crawl for SMVITM website.
This script crawls every internal page under https://sode-edu.in/smvitm/ and stores the results in data/scraped_data.json.
Improvements:
- Captures image metadata (alt text, titles)
- Finds hidden links in data attributes
- Better content extraction
- Logs discovered resources
"""

import json
import os
import time
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE = "https://sode-edu.in/smvitm/"
ALLOWED_DOMAINS = {"sode-edu.in", "www.sode-edu.in"}
ALLOWED_PATH_PREFIX = "/smvitm"
IGNORE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".ico",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".zip",
    ".rar",
    ".tar",
    ".gz",
    ".mp3",
    ".mp4",
    ".webm",
    ".ogg",
    ".css",
    ".js",
)


def make_session():
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    )
    return session


def normalize_url(url: str):
    if not url:
        return None

    parsed = urlparse(urljoin(BASE, url))
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    if scheme not in ("http", "https"):
        return None
    if netloc not in ALLOWED_DOMAINS:
        return None
    if not parsed.path.startswith(ALLOWED_PATH_PREFIX):
        return None

    path = parsed.path.rstrip("/")
    if not path:
        path = "/"

    normalized = parsed._replace(path=path, fragment="").geturl()
    return normalized


def is_allowed_link(url: str):
    if not url:
        return False
    parsed = urlparse(url)
    lower_path = parsed.path.lower()
    if any(lower_path.endswith(ext) for ext in IGNORE_EXTENSIONS):
        return False
    return True


import xml.etree.ElementTree as ET


def parse_sitemap(session, sitemap_url: str):
    urls = []
    try:
        resp = session.get(sitemap_url, timeout=20)
    except Exception:
        return urls

    if resp.status_code != 200 or not resp.text:
        return urls

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError:
        return urls

    for loc in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
        if loc.text:
            normalized = normalize_url(loc.text.strip())
            if normalized and is_allowed_link(normalized):
                urls.append(normalized)

    # Fallback if namespace-less sitemap tags are used
    if not urls:
        for loc in root.findall(".//loc"):
            if loc.text:
                normalized = normalize_url(loc.text.strip())
                if normalized and is_allowed_link(normalized):
                    urls.append(normalized)

    return urls


def extract_links(soup: BeautifulSoup, current_url: str):
    """Extract all types of links including hidden ones in data attributes"""
    links = set()
    
    # Regular anchor links
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue

        normalized = normalize_url(href)
        if normalized and is_allowed_link(normalized):
            links.add(normalized)
    
    # Links in data attributes
    for elem in soup.find_all(True):
        for attr in ["data-href", "data-link", "data-url", "data-target"]:
            href = elem.get(attr, "")
            if href:
                normalized = normalize_url(href)
                if normalized and is_allowed_link(normalized):
                    links.add(normalized)

    return links


def extract_images_metadata(soup: BeautifulSoup):
    """Extract image metadata (alt text, titles, src)"""
    images = []
    for img in soup.find_all("img"):
        img_data = {
            "src": img.get("src", ""),
            "alt": img.get("alt", ""),
            "title": img.get("title", ""),
        }
        if img_data["src"]:
            images.append(img_data)
    return images


def extract_text(html: str, url: str):
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "iframe",
        ]
    ):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else url

    container = soup.find("main") or soup.find("article") or soup.body or soup
    blocks = []

    for el in container.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th", "span", "div"], recursive=True
    ):
        text = el.get_text(" ", strip=True)
        if not text or len(text) < 3:
            continue

        if el.name == "li":
            blocks.append(f"- {text}")
        elif el.name == "h1":
            blocks.append(f"\n## {text}")
        elif el.name == "h2":
            blocks.append(f"\n## {text}")
        elif el.name in ("h3", "h4", "h5", "h6"):
            blocks.append(f"\n# {text}")
        else:
            blocks.append(text)

    content = "\n".join(blocks).strip()
    
    # Extract additional metadata
    images = extract_images_metadata(soup)
    links = extract_links(soup, url)
    
    # Add image metadata to content if present
    if images:
        content += "\n\n[IMAGES FOUND]:\n"
        for img in images[:10]:  # Limit to 10 images per page
            if img["alt"]:
                content += f"- {img['alt']}\n"
            elif img["title"]:
                content += f"- {img['title']}\n"
    
    return title, content, links


def save_scraped_data(scraped, path="data/scraped_data.json"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(scraped, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved {len(scraped)} pages to {path}")


def crawl(max_pages: int = None):
    session = make_session()
    queue = [BASE]
    visited = set()
    failed_count = 0
    scraped = []
    failed_urls = []

    print(f"🕷️  Starting comprehensive crawl from {BASE}")
    print(f"⚙️  Looking for sitemap.xml...\n")

    sitemap_candidates = [
        "https://sode-edu.in/smvitm/sitemap.xml",
        "https://sode-edu.in/sitemap.xml",
        "https://www.sode-edu.in/sitemap.xml",
    ]
    
    total_sitemap_urls = 0
    for sitemap_url in sitemap_candidates:
        try:
            sitemap_urls = parse_sitemap(session, sitemap_url)
            for url in sitemap_urls:
                # Skip very old archived pages (404s)
                if any(marker in url.lower() for marker in ["-2014", "-2013", "-2012", "bantakal-bags", "overview"]):
                    continue
                if url not in queue and url not in visited:
                    queue.append(url)
                    total_sitemap_urls += 1
            if sitemap_urls:
                print(f"✓ Loaded {len(sitemap_urls)} URLs (filtered {len(sitemap_urls)-total_sitemap_urls}) from {sitemap_url}")
        except Exception as e:
            print(f"⚠️  Could not load sitemap {sitemap_url}: {e}")

    print(f"\n📋 Total URLs in queue: {len(queue)}")
    print(f"🔄 Starting page crawl...\n")

    retry_count = {}
    max_retries = 2

    while queue:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        print(f"[{len(scraped)+1}] Fetching: {url}")
        try:
            response = session.get(url, timeout=30)  # Increased timeout
            response.raise_for_status()
        except requests.exceptions.Timeout:
            print(f"    ⏱️  Timeout - retrying...")
            if url not in retry_count:
                retry_count[url] = 0
            if retry_count[url] < max_retries:
                retry_count[url] += 1
                queue.append(url)
            else:
                failed_urls.append({"url": url, "error": "Timeout (after retries)"})
                failed_count += 1
            continue
        except Exception as exc:
            print(f"    ❌ Failed: {exc}")
            failed_urls.append({"url": url, "error": str(exc)})
            failed_count += 1
            continue

        if response.status_code != 200:
            print(f"    ⚠️  Skipped (status {response.status_code})")
            failed_urls.append({"url": url, "error": f"HTTP {response.status_code}"})
            failed_count += 1
            continue

        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            print(f"    ⚠️  Skipped (non-HTML: {content_type})")
            continue

        try:
            title, content, links = extract_text(response.text, url)
            if content:
                scraped.append({"url": url, "title": title, "content": content})
                print(f"    ✓ Saved ({len(content)} chars, {len(links)} links found)")
            else:
                scraped.append({"url": url, "title": title, "content": ""})
                print(f"    ✓ Saved (no content extracted)")

            for link in sorted(links):
                if link not in visited and link not in queue:
                    # Skip obviously old/archived links
                    if any(marker in link.lower() for marker in ["-2014", "-2013", "-2012"]):
                        continue
                    queue.append(link)
        except Exception as e:
            print(f"    ❌ Parse error: {e}")
            failed_urls.append({"url": url, "error": f"Parse error: {e}"})
            failed_count += 1
            continue

        if max_pages and len(scraped) >= max_pages:
            print(f"\n✓ Reached max_pages={max_pages}")
            break

        if len(scraped) % 5 == 0:
            save_scraped_data(scraped)

        time.sleep(0.2)  # Reduced delay

    save_scraped_data(scraped)
    
    # Summary report
    print(f"\n{'='*60}")
    print(f"📊 CRAWL SUMMARY")
    print(f"{'='*60}")
    print(f"✓ Scraped: {len(scraped)} pages")
    print(f"✓ Visited: {len(visited)} URLs")
    print(f"✓ Queue size: {len(queue)}")
    print(f"❌ Failed: {len(failed_urls)} URLs")
    print(f"{'='*60}\n")
    
    if failed_urls and len(scraped) == 0:
        print(f"⚠️  No pages scraped. First 5 errors:")
        for item in failed_urls[:5]:
            print(f"  - {item['url']}: {item['error']}")


if __name__ == "__main__":
    crawl()
