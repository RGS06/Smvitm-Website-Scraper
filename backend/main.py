from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import json
import os
import requests
import base64
import io
from dotenv import load_dotenv, find_dotenv
import re
import math
from collections import Counter, defaultdict
from gtts import gTTS
import numpy as np
import os.path
import hashlib

# Load environment variables and configure AI client
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path, override=True)
else:
    load_dotenv(override=True)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MURF_API_KEY = os.getenv("MURF_API_KEY")
model = None


def configure_ai_client():
    global GOOGLE_API_KEY, MURF_API_KEY, model
    dotenv_path = find_dotenv()
    if dotenv_path:
        load_dotenv(dotenv_path, override=True)
    else:
        load_dotenv(override=True)
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    MURF_API_KEY = os.getenv("MURF_API_KEY")

    if GOOGLE_API_KEY:
        try:
            genai.configure(api_key=GOOGLE_API_KEY)
            # Try primary model first, fallback to others if needed
            model = genai.GenerativeModel("gemini-2.5-flash")
            print("AI configured successfully (gemini-2.5-flash).")
        except Exception as e:
            print(f"gemini-2.5-flash failed: {e}. Trying gemini-2.0-flash...")
            try:
                model = genai.GenerativeModel("gemini-2.0-flash")
                print("AI configured successfully (gemini-2.0-flash).")
            except Exception as e2:
                print(f"gemini-2.0-flash failed: {e2}. Trying gemini-1.5-pro...")
                try:
                    model = genai.GenerativeModel("gemini-1.5-pro")
                    print("AI configured successfully (gemini-1.5-pro).")
                except Exception as e3:
                    print(f"AI configuration failed: {e3}")
                    model = None
    else:
        model = None
        print("WARNING: GOOGLE_API_KEY not found. AI features are disabled.")


configure_ai_client()
auto_ai_enabled = bool(GOOGLE_API_KEY)

app = FastAPI()

# --- SYNONYM / ACRONYM EXPANSION ---
# Maps short acronyms and common terms to expanded search terms
SYNONYM_MAP = {
    "pg": ["postgraduate", "post graduate", "m.tech", "mtech", "mba", "master", "ph.d", "phd", "doctoral", "admissions", "m tech", "higher studies"],
    "ug": ["undergraduate", "under graduate", "b.e", "b.e.", "bachelor", "engineering admission", "branches", "courses", "cse", "ece", "me", "civil", "aids", "aiml", "study", "degree"],
    "mba": ["mba", "master of business administration", "business administration", "management", "postgraduate", "finance", "marketing", "hr"],
    "mtech": ["m.tech", "mtech", "master of technology", "postgraduate", "specialization"],
    "m.tech": ["m.tech", "mtech", "master of technology", "postgraduate"],
    "phd": ["phd", "ph.d", "ph.d.", "doctorate", "doctoral", "research", "scholar"],
    "ph.d": ["phd", "ph.d", "ph.d.", "doctorate", "doctoral", "research"],
    "cse": ["computer science", "cse", "cs", "computer science engineering", "programming", "coding", "software"],
    "ece": ["electronics", "ece", "ec", "electronics communication", "electronics & communication", "circuits", "hardware"],
    "me": ["mechanical", "mechanical engineering", "mech", "machines", "workshop"],
    "mechanical": ["mechanical", "mechanical engineering", "me", "mech", "machines"],
    "civil": ["civil", "civil engineering", "construction", "structure"],
    "aids": ["artificial intelligence", "data science", "ai&ds", "aids", "analytics"],
    "aiml": ["artificial intelligence", "machine learning", "ai&ml", "aiml", "intelligence"],
    "ai": ["artificial intelligence", "ai", "aiml", "aids", "future tech"],
    "placement": ["placement", "placements", "placed", "recruiting", "recruitment", "career", "campus", "jobs", "offers", "salary", "package", "hiring", "work", "companies", "jobs", "ctc"],
    "fee": ["fee", "fees", "fee structure", "tuition", "payment", "bank", "account", "cost", "price", "money", "pay", "cash", "amount", "bill", "scholarship"],
    "hostel": ["hostel", "hostels", "accommodation", "boys hostel", "girls hostel", "residence", "stay", "room", "food", "mess", "living", "staying"],
    "scholarship": ["scholarship", "scholarships", "financial aid", "concession", "grant", "help", "money support"],
    "admission": ["admission", "admissions", "intake", "eligibility", "entrance", "cet", "kcet", "comedk", "quota", "seat", "join", "apply", "procedure", "how to get in", "enroll", "form"],
    "faculty": ["faculty", "professor", "teacher", "staff", "hod", "head of department", "instructors", "teaching", "lecturer", "list of teachers", "mentors", "guide"],
    "lab": ["laboratory", "lab", "labs", "laboratories", "practical", "experiments"],
    "library": ["library", "central library", "digital library", "books", "reading", "study hall"],
    "sports": ["sports", "games", "athletics", "tournament", "cricket", "football", "gym", "physical education", "play"],
    "nba": ["nba", "national board of accreditation", "accreditation", "quality"],
    "naac": ["naac", "national assessment", "accreditation", "grade"],
    "nirf": ["nirf", "ranking", "national institutional ranking", "rank"],
    "autonomous": ["autonomous", "autonomy", "university grants", "status"],
    "principal": ["principal", "director", "head", "chief", "boss", "leader"],
    "hod": ["hod", "head of department", "head", "boss", "chief", "in charge"],
    "exam": ["exam", "examination", "vtu", "semester", "internal assessment", "test", "results", "marks", "grade", "score", "passing"],
    "club": ["club", "clubs", "student club", "technical club", "cultural club", "extra curricular"],
    "event": ["event", "events", "fest", "festival", "celebration", "techfest", "cultural", "programme", "function"],
    "research": ["research", "publication", "journal", "conference", "paper", "policy", "framework", "scheme", "aditya kudva", "innovation", "discovery"],
    "policy": ["policy", "research policy", "framework", "guidelines", "rules"],
    "framework": ["framework", "policy", "research policy", "structure"],
    "lateral": ["lateral", "lateral entry", "diploma", "dcet"],
    "management quota": ["management quota", "management seat", "direct admission"],
    "contact": ["contact", "phone", "email", "address", "location", "bantakal", "office", "reach", "call", "mail", "where is"],
    "history": ["history", "background", "about", "established", "founded", "journey", "milestones", "when started"],
    "list": ["list", "names", "show me", "tell me", "provide", "all", "every"],
}

# Common stopwords for query tokenization — only the most absolute noise
STOPWORDS = {
    "the", "and", "a", "an", "it", "be", "as", "at", "by", "or", "if", "not", "will", "this", "that"
}


# Helper guard for missing AI configuration
def ensure_ai_enabled():
    if model is None:
        configure_ai_client()
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="AI is not configured. Set GOOGLE_API_KEY in .env to enable chat.",
        )


def is_noise_text(line: str) -> bool:
    """Filter out navigation elements, links, and other non-informational text."""
    text = line.strip()
    if not text:
        return True
    lower = text.lower()
    # Use slightly less aggressive length filtering for headers
    if len(text) < 15 and any(marker in lower for marker in ["department", "admission", "program", "course"]):
        return False
    # Navigation / boilerplate markers
    noise_markers = [
        "learn more", "click here", "read more", "view more",
        "powered with", "codenroll", "accessibility toolbar",
        "skip to content", "toggle navigation", "search for:",
        "© copyright", "all rights reserved", "cookie policy",
        "privacy policy", "terms of use", "powered by ai",
    ]
    if any(marker in lower for marker in noise_markers):
        return True
    if "🔗" in text or "→" in text:
        return True
    # Lines that are just pure contact info / links (not inside a paragraph)
    if len(text) < 50 and any(
        marker in text
        for marker in ["http", "www.", "@", "tel:", "+91"]
    ):
        return True
    # Lines that are just menu items (very short, start with -)
    if text.startswith("- ") and len(text) < 25:
        return True
    return False


def clean_content(content: str) -> str:
    """Clean scraped content by removing navigation junk and normalizing whitespace."""
    lines = content.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if is_noise_text(stripped):
            continue
        # Remove lines that are just CET codes, phone numbers etc
        if re.match(r'^[-•]\s*\+?\d[\d\s\-()]+$', stripped):
            continue
        if re.match(r'^[-•]\s*CET\s*CODE', stripped, re.IGNORECASE):
            continue
        # Keep the line
        cleaned.append(stripped)
    return "\n".join(cleaned)


def create_chunks(content: str, title: str, url: str, max_chunk_size: int = 800, overlap: int = 100) -> list:
    """Create overlapping text chunks from content for better retrieval."""
    content = clean_content(content)
    if not content.strip():
        return []

    # Split into paragraphs (separated by double newlines or heading markers)
    sections = re.split(r'\n(?=##?\s)', content)  # Split at headings
    
    chunks = []
    current_chunk = ""
    current_heading = ""
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
        
        # Detect heading
        heading_match = re.match(r'^(##?\s+.+)', section)
        if heading_match:
            current_heading = heading_match.group(1).strip()
        
        paragraphs = section.split("\n")
        for para in paragraphs:
            para = para.strip()
            if not para or len(para) < 10:
                continue
            
            if len(current_chunk) + len(para) > max_chunk_size and current_chunk:
                # Save current chunk
                chunk_text = current_chunk.strip()
                if len(chunk_text) > 40:
                    chunks.append(chunk_text)
                # Start new chunk with overlap — keep last part of previous
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else ""
                current_chunk = overlap_text + "\n" + para
            else:
                current_chunk += "\n" + para
    
    # Don't forget the last chunk
    if current_chunk.strip() and len(current_chunk.strip()) > 40:
        chunks.append(current_chunk.strip())
    
    # If content was too small for chunking, use entire content
    if not chunks and len(content.strip()) > 40:
        chunks.append(content.strip())
    
    return chunks


# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Load scraped data
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "scraped_data.json")
indexed_chunks = []

try:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Compute a hash of the data for cache invalidation
    data_hash = hashlib.md5(json.dumps([d.get("content", "") for d in raw_data], sort_keys=True).encode()).hexdigest()

    for item in raw_data:
        content = str(item.get("content") or "")
        title = str(item.get("title") or "")
        url = str(item.get("url") or "")

        # Use improved chunking
        chunks = create_chunks(content, title, url)
        
        for chunk_text in chunks:
            # Filter out navigation-heavy chunks
            dept_keywords = [
                "Computer Science", "Electronics", "Mechanical",
                "Civil", "Artificial Intelligence", "Data Science",
                "Machine Learning",
            ]
            mention_count = sum(1 for d in dept_keywords if d.lower() in chunk_text.lower())
            
            # If mentions 4+ departments in a short chunk, it's likely a sidebar/menu
            if mention_count > 3 and len(chunk_text) < 600:
                continue
            
            # Skip chunks that are mostly bullet-point lists of links
            if chunk_text.count("- ") > 10 and len(chunk_text) < 500:
                continue

            indexed_chunks.append({
                "content": chunk_text,
                "title": title,
                "url": url,
                "source": url,
                "title_lower": title.lower(),
                "content_lower": chunk_text.lower(),
            })

    print(f"Successfully loaded {len(indexed_chunks)} chunks from knowledge base.")
except Exception as e:
    print(f"Error loading data: {e}")
    import traceback
    traceback.print_exc()

# --- AI EMBEDDING INITIALIZATION ---
chunk_embeddings = None

@app.on_event("startup")
async def startup_event():
    # Start background embedding initialization - DISABLED FOR USER TESTING TO SAVE QUOTA
    # asyncio.create_task(initialize_embeddings())
    pass

async def initialize_embeddings():
    global chunk_embeddings
    try:
        import asyncio
        if not indexed_chunks or not auto_ai_enabled:
            return

        texts_to_embed = [
            f"Title: {c['title']}\nContent: {c['content']}" for c in indexed_chunks
        ]
        EMBEDDINGS_FILE = os.path.join(
            os.path.dirname(__file__), "..", "data", "chunk_embeddings.npy"
        )
        EMBEDDINGS_HASH_FILE = os.path.join(
            os.path.dirname(__file__), "..", "data", "embeddings_hash.txt"
        )

        # Check if cached embeddings match current data
        cache_valid = False
        if os.path.exists(EMBEDDINGS_FILE) and os.path.exists(EMBEDDINGS_HASH_FILE):
            try:
                with open(EMBEDDINGS_HASH_FILE, "r") as hf:
                    cached_hash = hf.read().strip()
                if cached_hash == data_hash:
                    # Use thread for IO to avoid blocking
                    print("Loading cached vector embeddings...")
                    chunk_embeddings = np.load(EMBEDDINGS_FILE)
                    if chunk_embeddings.shape[0] == len(indexed_chunks):
                        cache_valid = True
                        print(f"Cache valid: {chunk_embeddings.shape[0]} embeddings loaded.")
                    else:
                        print(f"Cache shape mismatch. Will re-embed.")
                        chunk_embeddings = None
            except Exception as e:
                print(f"Error loading cache: {e}")

        if not cache_valid:
            total_batches = (len(texts_to_embed) - 1) // 100 + 1
            print(f"\n[INIT] Generating vector embeddings for {len(texts_to_embed)} chunks ({total_batches} batches).")
            print(f"  System is active using Keyword Search during initialization.")
            
            embeddings_list = []
            batch_size = 100
            for i in range(0, len(texts_to_embed), batch_size):
                batch = texts_to_embed[i : i + batch_size]
                batch_num = i // batch_size + 1
                try:
                    # Threading for network call
                    loop = asyncio.get_event_loop()
                    resp = await loop.run_in_executor(None, lambda: genai.embed_content(
                        model="models/gemini-embedding-001",
                        content=batch,
                        task_type="retrieval_document",
                    ))
                    embeddings_list.extend(resp["embedding"])
                except Exception as batch_err:
                    err_str = str(batch_err)
                    if "429" in err_str or "quota" in err_str.lower():
                        if "Daily" in err_str or "Day" in err_str:
                            print(f"\n[CRITICAL] Daily Gemini Embedding Quota Exhausted. Using Keyword search fallback.")
                            break
                        print(f"  Rate limited. Waiting 70s for batch {batch_num}...")
                        await asyncio.sleep(70)
                        try:
                            resp = await loop.run_in_executor(None, lambda: genai.embed_content(
                                model="models/gemini-embedding-001", content=batch, task_type="retrieval_document")
                            )
                            embeddings_list.extend(resp["embedding"])
                        except:
                            print(f"  Retry failed for batch {batch_num}. Stopping embedding initialization.")
                            break
                    else:
                        print(f"  Embedding error: {batch_err}")
                        break
                
                # SIGNIFICANTLY slow down for free tier to leave room for chat!
                # 20s = 3 requests per minute. Free tier = ~15 RPM.
                await asyncio.sleep(20)

            if embeddings_list and len(embeddings_list) == len(texts_to_embed):
                chunk_embeddings = np.array(embeddings_list, dtype="float32")
                # IO in background
                await loop.run_in_executor(None, lambda: np.save(EMBEDDINGS_FILE, chunk_embeddings))
                with open(EMBEDDINGS_HASH_FILE, "w") as hf:
                    hf.write(data_hash)
                print(f"Successfully generated {chunk_embeddings.shape[0]} embeddings.")
            else:
                print("Using Keyword Search as primary engine (Embeddings partial/skipped).")
    except Exception as e:
        print(f"Background embedding initialization failed: {e}")



class ChatRequest(BaseModel):
    message: str


def expand_query(query: str) -> str:
    """Expand query with synonyms/acronyms to improve retrieval."""
    query_lower = query.lower().strip()
    tokens = re.findall(r'[\w.]+', query_lower)
    
    expanded_terms = set()
    for token in tokens:
        # Check exact token match in synonym map
        if token in SYNONYM_MAP:
            expanded_terms.update(SYNONYM_MAP[token])
        # Check multi-word phrases
        for key in SYNONYM_MAP:
            if key in query_lower:
                expanded_terms.update(SYNONYM_MAP[key])
    
    if expanded_terms:
        # Combine original query with expanded terms
        expansion = " ".join(expanded_terms - set(tokens))
        return f"{query} {expansion}"
    
    return query


def tokenize_query(query: str) -> list:
    """Tokenize query for keyword matching, keeping intent-defining words."""
    query_lower = re.sub(r"\s+", " ", query.lower()).strip()
    # Allow 2+ character tokens
    tokens = re.findall(r"\w[\w.]{1,}", query_lower)
    # Filter only most common stopwords, keep intent words
    result = [t for t in tokens if t not in STOPWORDS]
    
    # Also add synonym expansions as tokens
    for token in list(result):
        if token in SYNONYM_MAP:
            for syn in SYNONYM_MAP[token]:
                if syn not in result:
                    result.append(syn)
    
    return result


def keyword_search_context(query: str, max_chunks: int = 8) -> list:
    """Search chunks using keyword matching with fuzzy intent support."""
    if not indexed_chunks:
        return []

    query_lower = re.sub(r"\s+", " ", query.lower()).strip()
    
    # 1. Broad expansion
    expanded_query = expand_query(query)
    terms = tokenize_query(expanded_query)
    original_terms = tokenize_query(query)
    
    if not terms:
        terms = [w.lower() for w in query.split() if len(w) >= 2]
    
    # 2. IDF-like weights
    total_chunks = len(indexed_chunks)
    term_doc_counts = {}
    for term in terms:
        term_doc_counts[term] = sum(1 for chunk in indexed_chunks if term in chunk["content_lower"] or term in chunk["title_lower"])

    def term_weight(term: str) -> float:
        df = term_doc_counts.get(term, 0)
        if df <= 0: return 0.5
        ratio = df / total_chunks
        if ratio > 0.4: return 0.2
        if ratio > 0.2: return 0.5
        if ratio > 0.05: return 0.8
        return 1.2

    # 3. Dept names for soft boosting
    dept_names = ["mechanical", "civil", "computer science", "electronics", "artificial intelligence", "mba", "business administration"]
    queried_depts = [d for d in dept_names if d in query_lower]

    scores = []
    for chunk in indexed_chunks:
        score = 0.0
        content = chunk["content_lower"]
        title = chunk["title_lower"]
        url = chunk.get("url", "").lower()

        # A. EXACT TITLE SIGNAL
        if query_lower in title:
            score += 120
        
        for orig in original_terms:
            if orig in title:
                score += 35 * term_weight(orig)

        # B. PHRASE MATCHING
        for i in range(len(original_terms) - 1):
            phrase = f"{original_terms[i]} {original_terms[i+1]}"
            if phrase in title: score += 60
            if phrase in content: score += 25

        # C. TERM FREQUENCY + IDF (Sublinear)
        for term in terms:
            weight = term_weight(term)
            is_original = term in original_terms
            multiplier = 1.6 if is_original else 0.6
            
            t_count = title.count(term)
            c_count = content.count(term)
            
            if t_count > 0:
                score += (25 + (5 * math.log1p(t_count))) * weight * multiplier
            if c_count > 0:
                score += (8 + (3 * math.log1p(c_count))) * weight * multiplier

        # D. SOFT DEPT BOOST
        found_dept = False
        for d in queried_depts:
            if d in title or d in url:
                score += 50
                found_dept = True
            elif d in content:
                score += 20
                found_dept = True
        
        # If user asked about a dept and this is definitely a DIFFERENT dept's main page, 
        # apply a STRONG discount to prevent pollution of the context with wrong HODs.
        if queried_depts and not found_dept:
            other_dept_in_title = any(d in title for d in dept_names if d not in queried_depts)
            if other_dept_in_title:
                score *= 0.1 # Stronger discount for wrong-dept noise

        if score > 0:
            scores.append((score, chunk))

    if not scores:
        return indexed_chunks[:max_chunks]

    scores.sort(key=lambda x: x[0], reverse=True)
    
    selected = []
    seen_contents = set()
    for _, chunk in scores:
        ckey = chunk["content"][:150]
        if ckey not in seen_contents:
            selected.append(chunk)
            seen_contents.add(ckey)
        if len(selected) >= max_chunks:
            break
            
    return selected


async def get_relevant_context(query: str, max_chunks: int = 15) -> list:
    """Hybrid search: semantic (embeddings) + keyword, merged and deduplicated."""
    if not indexed_chunks:
        return []

    # Multi-query expansion for better recall (industry best practice to avoid 'fixed' logic)
    search_queries = [query]
    q_lower = query.lower()
    
    # 1. Smarter intent-based expansion
    intent_mappings = [
        (["hod", "head", "principal", "who", "boss", "chief", "leader"], "department leadership faculty staff professors head"),
        (["admission", "join", "eligibility", "how", "apply", "enroll"], "admission criteria portal process requirements application entrance"),
        (["fee", "cost", "money", "pay", "price", "amount"], "tuition fee structure bank details payment account scholarship"),
        (["place", "job", "career", "salary", "hiring", "company"], "placement records recruitment companies salary package drive"),
        (["where", "location", "address", "reach", "way"], "contact address location map reach office bantakal"),
        (["about", "info", "history", "what is", "college"], "about smvitm history mission vision overview establishment")
    ]
    
    for keywords, expansion in intent_mappings:
        if any(w in q_lower for w in keywords):
            search_queries.append(expansion)
    
    # If query is still very short/vague, add a general college overview search
    if len(q_lower.split()) < 3:
        search_queries.append("Shri Madhwa Vadiraja Institute of Technology Management overview courses departments")

    all_combined = []
    seen_chunks = set()
    
    # 2. Semantic (Embedding) Search
    try:
        # Only try embeddings if we haven't hit a retry/backoff recently
        if chunk_embeddings is not None and auto_ai_enabled:
            loop = asyncio.get_event_loop()
            # Expand the query with synonyms for a better semantic hit
            expanded_vec_query = expand_query(query)
            
            # Using a tighter timeout and a skip-logic if quota is likely tight
            vec_resp = await asyncio.wait_for(loop.run_in_executor(None, lambda: genai.embed_content(
                model="models/gemini-embedding-001", content=expanded_vec_query, task_type="retrieval_query"
            )["embedding"]), timeout=5.0)
            
            if vec_resp:
                query_vec = np.array(vec_resp, dtype="float32")
                norms = np.linalg.norm(chunk_embeddings, axis=1) * np.linalg.norm(query_vec)
                sims = np.dot(chunk_embeddings, query_vec) / np.maximum(norms, 1e-9)
                top_idxs = np.argsort(sims)[::-1][:max_chunks * 2]
                for idx in top_idxs:
                    # Loosen threshold for better 'fuzzy' recall (0.12 instead of 0.15)
                    if sims[idx] > 0.12: 
                        c = indexed_chunks[idx]
                        ckey = c["content"].strip()[:200]
                        if ckey not in seen_chunks:
                            all_combined.append(c)
                            seen_chunks.add(ckey)
    except Exception as e:
        print(f"Semantic search skipped to prioritize chat response: {e}")

    # 3. Keyword Search Hybrid (using multiple variations for recall)
    for s_query in search_queries[:3]: # Use up to 3 queries for better coverage
        keyword_results = keyword_search_context(s_query, max_chunks if s_query == query else 8)
        for c in keyword_results:
            ckey = c["content"].strip()[:200]
            if ckey not in seen_chunks:
                all_combined.append(c)
                seen_chunks.add(ckey)
    
    # 4. Mandatory Base Coverage (Ensure we never return 'nothing' if we have data)
    # If we have very few results, inject the 'Home/About' chunks as anchor context
    if len(all_combined) < 5 and len(indexed_chunks) > 0:
        # Fallback to the first few chunks (usually home page) and any chunk with 'About' in title
        for i in range(min(3, len(indexed_chunks))):
            c = indexed_chunks[i]
            ckey = c["content"].strip()[:200]
            if ckey not in seen_chunks:
                all_combined.append(c)
                seen_chunks.add(ckey)
        
        # Also look for 'About' or 'Overview' specific chunks
        for c in indexed_chunks:
            if any(w in c["title_lower"] for w in ["about", "overview", "admission"]):
                ckey = c["content"].strip()[:200]
                if ckey not in seen_chunks:
                    all_combined.append(c)
                    seen_chunks.add(ckey)
            if len(all_combined) >= 10:
                break
            
    return all_combined[:max_chunks]

@app.post("/chat")
async def chat(request: ChatRequest):
    user_query = request.message.strip()
    print(f"\n{'='*60}")
    print(f"Received query: {user_query}")
    # Give the AI MAXIMUM context (50 chunks) for EVERY query. 
    # Gemini 1.5/2.0 Flash can easily process 100k+ tokens - No reason to limit the 'big picture'.
    query_max_chunks = 50 

    # 1. Get context
    try:
        context_chunks = await get_relevant_context(user_query, max_chunks=query_max_chunks)
        
        context_str = ""
        source_links = []
        
        seen_urls = set()
        for i, c in enumerate(context_chunks):
            title = c.get("title", f"Source {i+1}")
            content = c.get("content", "")
            url = c.get("url", "")
            
            context_str += f"--- SOURCE {i+1}: {title} ---\n{content}\n\n"
            
            if url and url not in seen_urls:
                # Clean url for display
                display_title = title.replace(" - sode-edu.in/smvitm", "").strip()
                source_links.append({"title": display_title, "url": url})
                seen_urls.add(url)
        
        print(f"Retrieved {len(context_chunks)} context chunks.")
    except Exception as e:
        print(f"Error in context retrieval: {e}")
        import traceback
        traceback.print_exc()
        context_str = "Error finding specific context."
        source_links = []

    if not context_chunks:
        return {
            "response": "I couldn't find specific information about that in the SMVITM knowledge base. Please try rephrasing your question or ask about admissions, departments, placements, or campus facilities.",
            "sources": [],
        }

    # 2. Build prompt
    prompt = f"""You are the "SMVITM Virtual Assistant", an intelligent AI for Shri Madhwa Vadiraja Institute of Technology and Management (SMVITM), Bantakal.

### YOUR TASK:
You are the **Ultimate SMVITM Encyclopedia**. Forget 'fixed' or 'standard' responses. Your goal is to provide a predictive, thorough, and highly natural 'ChatGPT-like' answer based on EVERYTHING found in the context. 

If the user query is vague or doesn't match perfectly, use the provided context to offer the most logical related information. DO NOT say "I don't know" or "I couldn't find" if there is ANY related information in the context (e.g., if they ask for a 'boss', tell them about the HOD or Principal).

### SPECIFIC STAFF/HOD RULES:
- If asked for a "boss", "head", or "HOD" of a department, look for the person with the designation "Head of Department" or "Associate Professor & Head" in the specific department's context chunk.
- For Computer Science (CSE), the HOD is **Dr. Sadananda L**.
- For Mechanical, the HOD is **Dr. Sudarshan Rao K** (or the HOD designated in the latest Mechanical chunk).
- Prioritize current staff lists over old news items.

### UNIVERSAL GUIDELINES:
1. **Interpret Intent** — The user might use informal words or phrase things differently. Look for the "spirit" of the question. Even if the context doesn't have an exact word match, explain the most relevant information you have. 
2. **Predictive Accuracy** — Don't just answer; predict what is most helpful. If they ask about a department, they probably want to know who is in charge (HOD) and what they study there.
3. **No Fixed Format** — Don't answer the same way every time. Be conversational.
4. **Be Proactive** — Include names, phone numbers, and emails whenever you see them in the context.
5. **No Negative Responses** — Avoid saying "I don't have information on X". Instead, say "Based on the SMVITM records, here is the information regarding [Related Topic]..." and be as helpful as possible.
6. **Tone** — Enthusiastic, knowledgeable, and professional.

### SMVITM KNOWLEDGE BASE:
{context_str}

### USER QUERY:
{user_query}

**ASSISTANT DYNAMIC RESPONSE:**"""

    # 2. Call AI with retry logic for total correctness
    ai_response = ""
    ensure_ai_enabled()
    
    # Internal retry logic for quota limit
    max_retries = 3
    retry_delay = 2  # Start with 2 seconds
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            ai_response = response.text
            break
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "quota" in err_msg.lower() or "resource" in err_msg.lower():
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Chat Rate limited (429). Waiting {wait_time}s before retry {attempt+1}/{max_retries-1}...")
                    import asyncio as _asyncio
                    await _asyncio.sleep(wait_time)
                    continue
                else:
                    # After all retries exhausted, return useful info from context
                    print(f"All retries exhausted for quota limit. Generating response from context only.")
                    ai_response = generate_context_response(user_query, context_chunks)
            else:
                print(f"ERROR: {e}")
                print(f"Not a quota error, using context fallback.")
                import traceback
                traceback.print_exc()
                ai_response = generate_context_response(user_query, context_chunks)
                break
    
    return {
        "response": ai_response,
        "sources": source_links[:8],
    }


def generate_context_response(query: str, chunks: list) -> str:
    """Generate a response based purely on context when AI is unavailable"""
    if not chunks:
        return "I'm experiencing temporary technical issues with the AI service. Please try again in 1-2 minutes."
    
    # Build a simple response from the context
    response = "Based on the available information from SMVITM's knowledge base:\n\n"
    
    # Extract relevant information
    for chunk in chunks[:3]:
        content = chunk.get("content", "").strip()
        title = chunk.get("title", "").strip()
        
        if content:
            # Take first 150 chars of content as summary
            summary = content[:200].rstrip() + ("..." if len(content) > 200 else "")
            response += f"**{title}**\n{summary}\n\n"
    
    response += "\n⚠️ *Due to temporary API limitations, this is a summary of available information. Please try again in 1-2 minutes for a more detailed AI-generated response.*"
    
    return response


@app.post("/chat/voice")
async def chat_voice(audio: UploadFile = File(...)):
    print("Received audio file")
    audio_data = await audio.read()
    ensure_ai_enabled()

    # 1. Transcribe the audio
    try:
        audio_part = {
            "mime_type": audio.content_type or "audio/webm",
            "data": audio_data,
        }
        transcription_prompt = "Transcribe the following user audio query accurately. Only return the spoken words."
        print("Calling Gemini for transcription...")
        transcription_response = model.generate_content(
            [transcription_prompt, audio_part]
        )
        user_query = transcription_response.text.strip()
        print(f"Transcribed User Query: {user_query}")
    except Exception as e:
        print(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail="Could not transcribe audio")

    # 2. Get context
    try:
        context_chunks = await get_relevant_context(user_query)
        if not context_chunks:
            context_str = "No specific information found on the website for this query."
        else:
            context_str = "\n\n".join(
                [
                    f"--- Source: {c['title']} ({c['source']}) ---\n{c['content']}"
                    for c in context_chunks
                ]
            )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Context retrieval error: {str(e)}"
        )

    # 3. Generate concise conversational response for voice
    prompt = f"""You are the "SMVITM Virtual Assistant". Answer directly based STRICTLY on the context below.

### RULES:
1. **No Filler**: Do NOT say "Certainly" or "I can help with that". START with your direct answer immediately.
2. **No Markdown**: Speak in a natural, continuous conversational flow. Do not output bullet points, hashes, or asterisks.
3. **Strict Grounding**: Only answer based on the provided explicit context. Do not invent information.
4. **Tone**: Polite, Natural Indian English.
5. **Common acronyms**: PG = Postgraduate, UG = Undergraduate, CSE = Computer Science, ECE = Electronics, AIDS = AI & Data Science, AIML = AI & ML.

### CONTEXT:
{context_str}

---
USER QUESTION: {user_query}

VOICE ANSWER:"""

    try:
        print("Calling Gemini for text response...")
        response = model.generate_content(prompt)
        text_response = response.text.replace("*", "").replace("#", "").strip()
        print(f"Generated Text: {text_response[:100]}...")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")

    # 4. Generate TTS via Murf.ai
    audio_url = ""
    try:
        import time

        murf_url = "https://api.murf.ai/v1/speech/stream"
        murf_headers = {
            "api-key": os.getenv("MURF_API_KEY"),
            "Content-Type": "application/json",
        }
        murf_payload = {
            "text": text_response,
            "voiceId": "Aarav",
            "model": "FALCON",
            "style": "Conversational",
        }
        print(f"Calling Murf.ai Aarav voice for {len(text_response)} chars...")
        murf_resp = requests.post(
            murf_url, json=murf_payload, headers=murf_headers, timeout=15
        )
        if murf_resp.status_code == 200:
            timestamp = int(time.time())
            audio_filename = f"voice_response_{timestamp}.wav"
            audio_path = os.path.join(
                os.path.dirname(__file__), "..", "frontend", audio_filename
            )

            # Clean up old voice files
            try:
                for f in os.listdir(
                    os.path.join(os.path.dirname(__file__), "..", "frontend")
                ):
                    if f.startswith("voice_response_") and f.endswith(".wav"):
                        os.remove(
                            os.path.join(os.path.dirname(__file__), "..", "frontend", f)
                        )
            except:
                pass

            with open(audio_path, "wb") as f:
                f.write(murf_resp.content)
            audio_url = f"/static/{audio_filename}?v={timestamp}"
            print(f"Murf TTS saved as {audio_filename}")
        else:
            print(f"Murf API failed: {murf_resp.status_code} - {murf_resp.text[:100]}")
    except Exception as e:
        print(f"Murf TTS Error: {e}")

    return {
        "user_query": user_query,
        "response": text_response,
        "audio_url": audio_url,
        "sources": [c["source"] for c in context_chunks] if context_chunks else [],
    }


from fastapi.staticfiles import StaticFiles

# Serve frontend static files - using html=True for cleaner URLs
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=frontend_path, html=True), name="static")


from fastapi.responses import RedirectResponse

@app.get("/")
async def root():
    # Redirect root to chatbot interface
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
