"""
Fast SMVITM Scraper - Get essential pages only
"""
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os

BASE = "https://sode-edu.in/smvitm/"
scraped = []

def extract_text(html, url):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title else url
    text = soup.get_text(separator='\n')
    return title, text.strip()

def scrape_page(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,*/*;q=0.8',
    }
    try:
        r = requests.get(url, headers=headers, timeout=15, verify=False)
        if r.status_code == 200 and 'text/html' in r.headers.get('Content-Type', ''):
            title, content = extract_text(r.text, url)
            return {"url": url, "title": title, "content": content}
    except Exception as e:
        print(f"❌ {url}: {e}")
    return None

# Essential pages to scrape
essential_pages = [
    "https://sode-edu.in/smvitm/",
    "https://sode-edu.in/smvitm/about",
    "https://sode-edu.in/smvitm/admissions",
    "https://sode-edu.in/smvitm/departments/cse",
    "https://sode-edu.in/smvitm/departments/ece",
    "https://sode-edu.in/smvitm/departments/me",
    "https://sode-edu.in/smvitm/departments/civil",
    "https://sode-edu.in/smvitm/departments/aiml",
    "https://sode-edu.in/smvitm/departments/aids",
    "https://sode-edu.in/smvitm/placements",
    "https://sode-edu.in/smvitm/faculty",
    "https://sode-edu.in/smvitm/contact",
]

print("🕷️  Fast SMVITM Scraper")
print("=" * 50)

for url in essential_pages:
    print(f"Fetching: {url}")
    result = scrape_page(url)
    if result:
        scraped.append(result)
        print(f"  ✓ Success ({len(result['content'])} chars)")
    else:
        print(f"  ⚠️  Failed")

# Save
os.makedirs("data", exist_ok=True)
with open("data/scraped_data.json", "w", encoding="utf-8") as f:
    json.dump(scraped, f, indent=2, ensure_ascii=False)

print("=" * 50)
print(f"✓ Scraped {len(scraped)} pages")
print(f"✓ Saved to data/scraped_data.json")
