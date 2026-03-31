import subprocess
import re
import os

SITEMAP_INDEX = "https://sode-edu.in/smvitm/wp-sitemap.xml"
HEADERS = [
    "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "-H", "Accept-Encoding: gzip, deflate, br",
    "-H", "Accept-Language: en-US,en;q=0.9"
]

def fetch_url(url):
    print(f"Fetching: {url}")
    try:
        cmd = ["curl.exe", "-s", "--compressed"] + HEADERS + [url]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        return result.stdout
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

def extract_urls(xml_content):
    return re.findall(r"<loc>(.*?)</loc>", xml_content)

def main():
    index_xml = fetch_url(SITEMAP_INDEX)
    sitemaps = extract_urls(index_xml)
    print(f"Found {len(sitemaps)} sub-sitemaps.")
    
    all_urls = set()
    for sitemap in sitemaps:
        sitemap_xml = fetch_url(sitemap)
        urls = extract_urls(sitemap_xml)
        print(f"  Got {len(urls)} URLs from {sitemap}")
        for u in urls:
            all_urls.add(u)
            
    with open("all_urls.txt", "w", encoding="utf-8") as f:
        for u in sorted(all_urls):
            f.write(u + "\n")
            
    print(f"\nDone! Total unique URLs: {len(all_urls)}. Saved to all_urls.txt")

if __name__ == "__main__":
    main()
