import json
import re

def find_hods():
    with open(r'd:\College Chat\CollegeChatbot\data\scraped_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = {}
    for d in data:
        url = d.get('url', '').lower()
        if 'departments/' in url:
            content = d.get('content', '')
            title = d.get('title', '').split('|')[0].strip()
            
            # Extract HOD name
            # Often near "Mr." or "Dr." or in faculty list
            match = re.search(r'(?:HOD|Head of the Department|Head of Department|Professor & Head)\s*[:\-]*\s*([A-Z][a-z\.\s]+[A-Z\.\s]+)', content, re.IGNORECASE)
            if match:
                name = match.group(1).strip().split('\n')[0].strip()
                if len(name) > 5:
                    results[title] = name
            else:
                # Fallback: look for faculty starting with Dr. or Mr. if no HOD mentioned explicitly near top
                match = re.search(r'(?:##|#)\s*(Dr\.\s+[A-Z][a-z\.\s]+|Mr\.\s+[A-Z][a-z\.\s]+)', content)
                if match:
                    results[title + " (Potential HOD)"] = match.group(1).strip()
                
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    find_hods()
