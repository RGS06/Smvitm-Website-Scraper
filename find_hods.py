import json
import re

def find_hods():
    with open(r'd:\College Chat\CollegeChatbot\data\scraped_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = {}
    for d in data:
        content = d.get('content', '')
        title = d.get('title', '')
        
        # Look for "HOD" or "Head of Department" followed by a name
        match = re.search(r'(?:HOD|Head of the Department|Head of Department)\s*[:\-]*\s*([A-Za-z\.\s]+)', content, re.IGNORECASE)
        if match:
            # Clean up the name
            name = match.group(1).strip().split('\n')[0]
            if len(name) > 3:
                results[title] = name
                
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    find_hods()
