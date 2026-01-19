from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
from typing import Optional, List, Dict
import re

KIWIX_BASE = "http://127.0.0.1:8091"

app = FastAPI(title="Kiwix Offline Wikipedia Tool", version="1.4.0")

# Allow browser-based clients if needed (OpenWebUI etc.)
# If you need cookies/auth, set allow_credentials=True and specify explicit origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Helpers
# -------------------------

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join([ln for ln in lines if ln])

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("_", " ").strip().lower())

def normalize_query(q: Optional[str]) -> str:
    """
    Jarvis CLI sometimes sends tool-routing prefixes like:
      - "wiki: Bremblens"
      - "wikipedia: Bremblens"
      - "kiwix: Bremblens"
      - "wiki Bremblens"
    Strip these so Kiwix search gets the real term.
    """
    s = (q or "").strip()

    # Strip leading prefixes with colon
    s = re.sub(r"^(wiki|wikipedia|kiwix)\s*:\s*", "", s, flags=re.IGNORECASE)

    # Strip "wiki " without colon
    s = re.sub(r"^(wiki|wikipedia|kiwix)\s+", "", s, flags=re.IGNORECASE)

    return s.strip()

def is_wiki_routed(raw: Optional[str]) -> bool:
    """
    Detect whether the caller intended a wiki lookup via prefix.
    """
    s = (raw or "").strip()
    return bool(re.match(r"^\s*(wiki|wikipedia|kiwix)\s*:", s, flags=re.IGNORECASE))

def _clean_title_from_href(href: str) -> str:
    # Handles:
    #  - /content/wikipedia_en_all_nopic/Bremblens  -> Bremblens
    #  - /A/Moons_of_Jupiter -> Moons of Jupiter
    #  - /wiki/Moons_of_Jupiter -> Moons of Jupiter
    parts = href.split("/")
    candidate = parts[-1] if parts else href
    candidate = unquote(candidate).replace("_", " ").strip()
    return candidate

def _is_article_href(href: str) -> bool:
    if not href or not href.startswith("/"):
        return False

    # Skip search controls/pagination
    if href.startswith("/search") or "search?" in href:
        return False

    # Your Kiwix uses /content/<zim_name>/<Title>
    if href.startswith("/content/"):
        return True

    # Other common Kiwix setups
    if href.startswith("/A/") or href.startswith("/wiki/"):
        return True

    return False

def _pick_results_root(soup: BeautifulSoup):
    # Your HTML showed `.results` and `.results li`
    for sel in [".results", "#results", "main", "#content"]:
        node = soup.select_one(sel)
        if node:
            return node
    return soup

async def kiwix_search_html(pattern: str, limit: int = 5) -> List[Dict[str, str]]:
    """
    Kiwix search returns HTML. We scrape result links.
    Returns list of {title, path}.
    """
    async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "Kiwix-Wrapper/1.4"}) as client:
        r = await client.get(f"{KIWIX_BASE}/search", params={"pattern": pattern})
        r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    root = _pick_results_root(soup)

    candidates: List[Dict[str, str]] = []
    seen = set()

    for a in root.select("a[href]"):
        href = a.get("href", "").strip()
        if not _is_article_href(href):
            continue

        if href in seen:
            continue
        seen.add(href)

        title_txt = " ".join(a.stripped_strings)
        title = title_txt if title_txt else _clean_title_from_href(href)

        if not title:
            continue
        tnorm = _norm(title)
        if tnorm in {"home", "search", "index"}:
            continue

        candidates.append({"title": title, "path": href})

    # Rank results so exact/close matches win
    qn = _norm(pattern)

    def rank(item):
        t = _norm(item["title"])
        if t == qn:
            return (0, len(t))
        if t.startswith(qn):
            return (1, len(t))
        if qn in t:
            return (2, len(t))
        return (3, len(t))

    candidates.sort(key=rank)

    return candidates[:limit]

async def fetch_page_text(path: str) -> str:
    async with httpx.AsyncClient(timeout=20.0, headers={"User-Agent": "Kiwix-Wrapper/1.4"}) as client:
        pr = await client.get(urljoin(KIWIX_BASE, path))
        pr.raise_for_status()
    return html_to_text(pr.text)

def extract_lede(text: str, max_len: int = 450) -> str:
    """
    Produce a cleaner lead sentence/paragraph for embedding in Jarvis evidence.
    Tries to avoid infobox spam.
    """
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]

    # Remove duplicate title lines at top
    if len(lines) >= 2 and lines[0].lower() == lines[1].lower():
        lines = lines[1:]

    cleaned = "\n".join(lines)

    # Prefer first line containing "is a"
    m = re.search(r"(^|\n)([^\n]{0,200}\bis a\b[^\n]{0,800})", cleaned, flags=re.IGNORECASE)
    if m:
        lede = m.group(2)
    else:
        # fallback: take first 2 lines
        lede = " ".join(lines[:2]) if lines else ""

    lede = re.sub(r"\s+", " ", lede).strip()
    if len(lede) > max_len:
        lede = lede[:max_len] + "…"
    return lede

# -------------------------
# API endpoints
# -------------------------

@app.get("/search")
async def search(
    # Accept both /search?q=... and /search?query=...
    q: Optional[str] = Query(None, description="Search query (preferred param: q)"),
    query: Optional[str] = Query(None, description="Search query (alias param: query)"),
    # Jarvis CLI sends this sometimes
    max_results: int = Query(10, ge=1, le=25, description="Max number of results to return"),
):
    term = normalize_query(q or query)
    if not term:
        return {"query": "", "results": [], "error": "Missing query param. Use ?q=... or ?query=..."}

    results = await kiwix_search_html(term, limit=max_results)

    # Jarvis CLI tends to call /search with max_results=2 and then never calls /page.
    # Since Jarvis only displays results[].title, we embed a short summary in the title.
    if results and max_results <= 2:
        top = results[0]
        page_text = await fetch_page_text(top["path"])

        summary = page_text.replace("\n", " ")
        summary = re.sub(r"\s+", " ", summary).strip()
        summary = summary[:600] + "…"

        return {
            "query": term,
            "results": [
                {
                    "title": f"{top['title']}: {summary}",
                    "path": top["path"],
                }
            ],
        }

    return {"query": term, "results": results}

@app.get("/page")
async def page(
    # Accept /page?title=..., but also handle /page?q=... or /page?query=...
    title: Optional[str] = Query(None, description="Exact article title (e.g., 'Moons of Jupiter')"),
    q: Optional[str] = Query(None, description="Alias query param"),
    query: Optional[str] = Query(None, description="Alias query param"),
    max_results: int = Query(5, ge=1, le=10, description="Number of candidate results to consider"),
):
    raw = title or q or query
    term = normalize_query(raw)
    if not term:
        return {"found": False, "title": "", "text": "", "error": "Missing title. Use ?title=... (or ?q / ?query)."}

    results = await kiwix_search_html(term, limit=max_results)
    if not results:
        return {"found": False, "title": term, "text": "", "error": "No results from Kiwix search."}

    top = results[0]
    text = await fetch_page_text(top["path"])

    return {
        "found": True,
        "title": top["title"],
        "path": top["path"],
        "text": text[:30000],
        "candidates": results[:max_results],
    }

@app.get("/lookup")
async def lookup(
    # One-shot: search + fetch.
    q: Optional[str] = Query(None, description="Lookup query (preferred param: q)"),
    query: Optional[str] = Query(None, description="Lookup query (alias param: query)"),
):
    raw = q or query
    term = normalize_query(raw)
    if not term:
        return {"found": False, "title": "", "text": "", "error": "Missing q/query."}

    results = await kiwix_search_html(term, limit=5)
    if not results:
        return {"found": False, "title": term, "text": "", "error": "No results from Kiwix search."}

    top = results[0]
    text = await fetch_page_text(top["path"])

    return {
        "found": True,
        "title": top["title"],
        "path": top["path"],
        "text": text[:30000],
        "candidates": results[:5],
    }

@app.get("/wiki")
async def wiki(
    # Jarvis-friendly single endpoint (always returns embedded lede in results[0].title)
    q: str = Query(..., description="Wiki query (can include wiki: prefix or plain term)"),
    max_len: int = Query(450, ge=120, le=900, description="Max embedded lede length"),
):
    term = normalize_query(q)
    results = await kiwix_search_html(term, limit=5)
    if not results:
        return {"query": term, "results": []}

    top = results[0]
    page_text = await fetch_page_text(top["path"])
    lede = extract_lede(page_text, max_len=max_len)

    return {
        "query": term,
        "results": [
            {"title": f"{top['title']}: {lede}", "path": top["path"]}
        ],
    }

@app.get("/debug_search_raw")
async def debug_search_raw(
    q: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
):
    raw = q or query
    term = normalize_query(raw)
    if not term:
        return {"error": "Missing q/query"}

    async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "Kiwix-Wrapper/1.4"}) as client:
        r = await client.get(f"{KIWIX_BASE}/search", params={"pattern": term})
        r.raise_for_status()

    return {"html": r.text[:20000]}
