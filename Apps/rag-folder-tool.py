from __future__ import annotations

import os
import json
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi


# ----------------------------
# App + CORS
# ----------------------------
app = FastAPI(title="RAG Folder Tool", version="1.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------
# Force OpenAPI 3.0.2 (OpenWebUI compatibility)
# ----------------------------
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["openapi"] = "3.0.2"
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


# ----------------------------
# Defaults
# ----------------------------
DEFAULT_DIRECTORY = os.environ.get("RAG_DIRECTORY", "/mnt/shared/rag")
DEFAULT_EXTS: Set[str] = {".jsonl", ".json", ".xml", ".txt", ".md", ".csv"}

DEFAULT_MAX_RESULTS = 25
DEFAULT_SNIPPET_CHARS = 1200

# For JSONL we stream; for others we cap reads
DEFAULT_MAX_BYTES_PER_FILE = 50_000_000  # 50MB


# ----------------------------
# Helpers
# ----------------------------
def _safe_realpath(path: str) -> str:
    return os.path.realpath(os.path.expanduser(path))


def _normalize_exts(exts: Optional[List[str]]) -> Set[str]:
    if not exts:
        return set(DEFAULT_EXTS)
    out: Set[str] = set()
    for e in exts:
        if not e:
            continue
        e = str(e).strip().lower()
        if not e:
            continue
        if not e.startswith("."):
            e = "." + e
        out.add(e)
    return out or set(DEFAULT_EXTS)


def _read_text_limited(file_path: str, max_bytes: int) -> str:
    with open(file_path, "rb") as f:
        data = f.read(max_bytes)
    return data.decode("utf-8", errors="replace")


def _find_snippet(haystack: str, needle: str, snippet_chars: int) -> Optional[str]:
    if snippet_chars <= 0:
        return None
    h_low = haystack.lower()
    n_low = needle.lower()
    idx = h_low.find(n_low)
    if idx == -1:
        return None
    start = max(0, idx - snippet_chars // 2)
    end = min(len(haystack), idx + len(needle) + snippet_chars // 2)
    snippet = haystack[start:end]
    if start > 0:
        snippet = "… " + snippet
    if end < len(haystack):
        snippet = snippet + " …"
    return snippet


def _extract_query(payload: Any) -> str:
    # 1) direct string
    if isinstance(payload, str):
        return payload.strip()

    # 2) object attributes
    for attr in ("query", "q", "text", "input", "prompt", "search", "term", "value"):
        if hasattr(payload, attr):
            v = getattr(payload, attr)
            if isinstance(v, str) and v.strip():
                return v.strip()

    # 3) dict
    if isinstance(payload, dict):
        for k in ("query", "q", "text", "input", "prompt", "search", "term", "value"):
            v = payload.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()

        nested_query = payload.get("query")
        if isinstance(nested_query, dict):
            for k in ("query", "q", "text", "input", "prompt", "search", "term", "value"):
                v = nested_query.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()

        tool_input = payload.get("tool_input") or payload.get("arguments") or payload.get("params")
        if isinstance(tool_input, dict):
            for k in ("query", "q", "text", "input", "prompt", "search", "term", "value"):
                v = tool_input.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()

        # last resort: first non-empty string anywhere
        def walk(x: Any) -> Optional[str]:
            if isinstance(x, str) and x.strip():
                return x.strip()
            if isinstance(x, dict):
                for vv in x.values():
                    got = walk(vv)
                    if got:
                        return got
            if isinstance(x, list):
                for vv in x:
                    got = walk(vv)
                    if got:
                        return got
            return None

        return walk(payload) or ""

    # 4) list
    if isinstance(payload, list):
        for item in payload:
            q = _extract_query(item)
            if q:
                return q

    return ""


def _search_json(text: str, q: str) -> bool:
    ql = q.lower()
    try:
        obj = json.loads(text)
        return ql in json.dumps(obj, ensure_ascii=False).lower()
    except Exception:
        return ql in text.lower()


def _search_xml(text: str, q: str) -> bool:
    ql = q.lower()
    try:
        xml_root = ET.fromstring(text)  # do NOT name this "root"
        xml_str = ET.tostring(xml_root, encoding="unicode")
        return ql in xml_str.lower()
    except Exception:
        return ql in text.lower()


def _search_jsonl_streaming(
    file_path: str, q: str, max_bytes: int, snippet_chars: int
) -> Optional[Dict[str, Any]]:
    ql = q.lower()
    bytes_read = 0

    with open(file_path, "rb") as f:
        for raw_line in f:
            bytes_read += len(raw_line)
            if bytes_read > max_bytes:
                break

            line = raw_line.decode("utf-8", errors="replace")
            if ql in line.lower():
                snippet = _find_snippet(line, q, snippet_chars) or line[: min(len(line), 4000)]
                return {
                    # OpenWebUI-friendly keys:
                    "file_path": file_path,
                    "content": line,     # full matched line (jsonl record)
                    # Extras:
                    "snippet": snippet,
                    "match_type": "jsonl",
                }
    return None


def search_files(
    directory: str,
    query: str,
    exts: Set[str],
    max_results: int,
    max_bytes_per_file: int,
    snippet_chars: int,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    q = query.strip()
    if not q:
        return results

    for dirpath, _, filenames in os.walk(directory):
        for fname in filenames:
            if len(results) >= max_results:
                return results

            ext = os.path.splitext(fname)[1].lower()
            if ext not in exts:
                continue

            file_path = os.path.join(dirpath, fname)

            try:
                if ext == ".jsonl":
                    hit = _search_jsonl_streaming(file_path, q, max_bytes_per_file, snippet_chars)
                    if hit:
                        results.append(hit)
                    continue

                text = _read_text_limited(file_path, max_bytes_per_file)

                matched = False
                if ext in {".txt", ".md", ".csv"}:
                    matched = q.lower() in text.lower()
                elif ext == ".json":
                    matched = _search_json(text, q)
                elif ext == ".xml":
                    matched = _search_xml(text, q)
                else:
                    matched = q.lower() in text.lower()

                if matched:
                    snippet = _find_snippet(text, q, snippet_chars) or text[: min(len(text), 4000)]
                    results.append(
                        {
                            # OpenWebUI-friendly keys:
                            "file_path": file_path,
                            "content": snippet,  # keep payload smaller than full file
                            # Extras:
                            "snippet": snippet,
                            "match_type": ext.lstrip(".") or "file",
                        }
                    )

            except Exception as e:
                print(f"Error reading {file_path}: {type(e).__name__}: {e}")

    return results


# ----------------------------
# Routes
# ----------------------------
@app.post("/search/")
async def search(payload: Any = Body(...)):
    directory = DEFAULT_DIRECTORY
    extensions: Optional[List[str]] = None
    max_results = DEFAULT_MAX_RESULTS
    max_bytes_per_file = DEFAULT_MAX_BYTES_PER_FILE
    snippet_chars = DEFAULT_SNIPPET_CHARS

    if isinstance(payload, dict):
        if isinstance(payload.get("directory"), str) and payload["directory"].strip():
            directory = payload["directory"].strip()
        if isinstance(payload.get("extensions"), list):
            extensions = payload.get("extensions")
        if isinstance(payload.get("max_results"), int):
            max_results = payload.get("max_results", max_results)
        if isinstance(payload.get("max_bytes_per_file"), int):
            max_bytes_per_file = payload.get("max_bytes_per_file", max_bytes_per_file)
        if isinstance(payload.get("snippet_chars"), int):
            snippet_chars = payload.get("snippet_chars", snippet_chars)

    query = _extract_query(payload)
    print(f"DEBUG extracted query: {query!r}")  # helps confirm OpenWebUI is sending the right thing

    if not query:
        raise HTTPException(status_code=400, detail="Missing query (expected 'query' or 'q')")

    directory = _safe_realpath(directory)
    if not os.path.isdir(directory):
        raise HTTPException(status_code=400, detail=f"Directory not found: {directory}")

    exts = _normalize_exts(extensions)

    results = search_files(
        directory=directory,
        query=query,
        exts=exts,
        max_results=max_results,
        max_bytes_per_file=max_bytes_per_file,
        snippet_chars=snippet_chars,
    )

    if not results:
        raise HTTPException(status_code=404, detail="No files found matching the query")

    return {"results": results}


@app.get("/")
def root():
    return {"status": "ok"}
