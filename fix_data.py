import json
import time
import requests
from bs4 import BeautifulSoup
import os
import re

BASE_TARGET = "https://sode-edu.in/smvitm/"

def make_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    })
    return session

def extract_text(html, url):
    soup = BeautifulSoup(html, "html.parser")
    # For common departments, keep more text
    is_dept = "departments/" in url or "admission" in url
    
    tags_to_remove = ["script", "style", "nav", "footer", "header", "aside", "form"]
    for tag in soup(tags_to_remove):
        tag.decompose()
        
    title = soup.title.string.strip() if soup.title and soup.title.string else url
    # Clean the title of the base url
    title = title.replace(" - sode-edu.in/smvitm", "").replace(" | sode-edu.in/smvitm", "")
    
    container = soup.find("main") or soup.find("article") or soup.body or soup
    blocks = []
    
    # Identify key headings for retrieval
    for el in container.find_all(["h1", "h2", "h3", "h4", "p", "li", "td", "th", "div"], recursive=True):
        if el.name == "div" and not list(el.children): continue # skip empty divs
        
        text = el.get_text(" ", strip=True)
        if not text or len(text) < 5: continue
        
        # Don't add nested text twice if it's already in parent
        if any(text in (b or "") for b in blocks[-3:]): continue
        
        if el.name == "li": blocks.append(f"- {text}")
        elif el.name in ("h1", "h2"): blocks.append(f"\n## {text}")
        elif el.name in ("h3", "h4"): blocks.append(f"\n# {text}")
        else: blocks.append(text)
        
    content = "\n".join(blocks).strip()
    return title, content

def fix_scraped_data():
    data_dir = r"d:\College Chat\CollegeChatbot\data"
    os.makedirs(data_dir, exist_ok=True)
    json_path = os.path.join(data_dir, "scraped_data.json")
    urls_path = os.path.join(data_dir, "urls.txt")
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            scraped = json.load(f)
    except:
        scraped = []
    
    current_urls = {item["url"].rstrip("/") for item in scraped}
    current_urls.update({item["url"] for item in scraped})
    
    with open(urls_path, "r", encoding="utf-8") as f:
        target_urls = [line.strip() for line in f if line.strip()]
        
    session = make_session()
    new_items = 0
    
    for url in target_urls:
        u = url.rstrip("/")
        if u in current_urls or url in current_urls:
            continue
            
        print(f"Fetching missing URL: {url}")
        try:
            resp = session.get(url, timeout=12)
            if resp.status_code == 200:
                title, content = extract_text(resp.text, url)
                if content:
                    scraped.append({"url": url, "title": title, "content": content})
                    new_items += 1
                    print(f"  Saved {title} ({len(content)} chars)")
            time.sleep(1.2)
        except Exception as e:
            print(f"Failed {url}: {e}")
            
    if new_items > 0:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(scraped, f, indent=2, ensure_ascii=False)
        print(f"DONE: Added {new_items} new pages to scraped_data.json.")
    else:
        print("All URLs in urls.txt are already present in JSON.")

if __name__ == "__main__":
    fix_scraped_data()
