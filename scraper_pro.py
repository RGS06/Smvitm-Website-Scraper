import json
import os
import time
import requests
import random
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://sode-edu.in/smvitm/"
ALLOWED_DOMAINS = {"sode-edu.in", "www.sode-edu.in"}
ALLOWED_PATH_PREFIX = "/smvitm"
OUTPUT_FILE = "scraper.json"
MAX_THREADS = 4
TIMEOUT = 45

def make_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
    })
    return session

def normalize_url(url: str):
    if not url: return None
    try:
        parsed = urlparse(urljoin(BASE, url))
        if parsed.netloc.lower() not in ALLOWED_DOMAINS: return None
        if not parsed.path.startswith(ALLOWED_PATH_PREFIX): return None
        return parsed._replace(scheme="https", fragment="").geturl().rstrip("/")
    except: return None

def extract_content(html: str, url: str):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe"]): tag.decompose()
    all_text = soup.get_text(separator=' ', strip=True)
    page_title = soup.title.string.strip() if soup.title else url
    
    images = []
    for img in soup.find_all("img"):
        src = img.get("src")
        if src:
            images.append({"src": urljoin(url, src), "alt": img.get("alt", ""), "title": img.get("title", "")})
            
    links = []
    found_urls = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        links.append({"text": anchor.get_text(strip=True), "href": urljoin(url, href)})
        norm = normalize_url(href)
        if norm and not any(norm.lower().endswith(ext) for ext in ('.pdf', '.jpg', '.png', '.zip', '.doc')):
            found_urls.add(norm)
            
    return {
        "url": url,
        "title": page_title,
        "content": all_text,
        "images": images,
        "links": links,
        "found_urls": list(found_urls)
    }

def scrape_one(url, session):
    try:
        time.sleep(random.uniform(0.5, 1.5))
        r = session.get(url, timeout=TIMEOUT)
        if r.status_code == 200 and 'text/html' in r.headers.get('Content-Type', ''):
            return extract_content(r.text, url)
        return {"url": url, "error": f"Status {r.status_code}"}
    except Exception as e:
        return {"url": url, "error": str(e)}

def main():
    scraped_data = []
    visited = set()
    queue = set()
    
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                scraped_data = json.load(f)
                for item in scraped_data:
                    visited.add(normalize_url(item["url"]))
            print(f"🔄 Loaded {len(scraped_data)} already-scraped pages.")
        except: pass
            
    if os.path.exists("all_urls.txt"):
        with open("all_urls.txt", "r", encoding="utf-8") as f:
            for line in f:
                u = normalize_url(line.strip())
                if u and u not in visited: queue.add(u)
    
    if not queue and len(visited) == 0: queue.add(BASE)
    
    print(f"📡 {len(queue)} pending URLs.")
    session = make_session()
    
    while queue:
        batch = list(queue)[:50]
        for u in batch: queue.remove(u)
        
        print(f"\n📦 Processing batch ({len(queue)} remaining in queue)...")
        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            future_to_url = {executor.submit(scrape_one, url, session): url for url in batch}
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                visited.add(url)
                result = future.result()
                if "error" not in result:
                    # Filter only keys for json
                    save_obj = {k: result[k] for k in ["url", "title", "content", "images", "links"]}
                    scraped_data.append(save_obj)
                    print(f"✅ {url}")
                    for f in result.get("found_urls", []):
                        if f not in visited: queue.add(f)
                else:
                    print(f"❌ {url}: {result['error']}")
        
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(scraped_data, f, indent=2, ensure_ascii=False)
        time.sleep(2)

    print(f"\nDone! Scraped {len(scraped_data)} items.")

if __name__ == "__main__":
    main()
