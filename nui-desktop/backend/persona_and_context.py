"""Official CosmicTera NUI Persona Loader, Intent & Response Mode Classifier, System Prompt Builder, and Domain-Gated Contextual Retriever.

Implements:
- Official NUI persona and system instructions directly from `src/hijaiyyah/ai/runtime.py`
  (`HybitAIProgram.system`), `AGENTS.md`, `cosmictera/RULES.md`, `NUI/LAYERS.md`, and `teknologi/ISTILAH.md`.
- Full General AI & Software Engineering Intelligence (Python, JS/TS, Swift, C/C++, HTML/CSS, Rust,
  REST API vs GraphQL, debugging, algorithms, databases, UI/UX, writing, math, reasoning) powered by Local LLM,
  with CosmicTera repository knowledge injected ONLY when the query is genuinely about CosmicTera.
- 8-Mode Intent & Response Classifier (`CONVERSATIONAL`, `CAPABILITY_INQUIRY`, `GENERAL_INTELLIGENCE`,
  `TECHNICAL`, `TASK_EXECUTION`, `REPOSITORY_AUDIT`, `DEEP_RESEARCH`, `SYSTEM_DIAGNOSTICS`).
- Domain-Gated & Word-Boundary Contextual Retrieval (`NUIContextualRetriever`) integrated
  with `src/hijaiyyah/nui/knowledge.py::query()` and `src/hijaiyyah/nui/usr.py::parse_phrase()`.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from hijaiyyah.ai.runtime import HybitAIProgram
from hijaiyyah.core.master_table import MASTER_TABLE
from hijaiyyah.hisa.opcodes import OpCode
from hijaiyyah.nui import (
    facts as nui_facts,
    knowledge as nui_knowledge,
    program_index,
    usr as nui_usr,
)

RESPONSE_MODES = (
    "CONVERSATIONAL",
    "CAPABILITY_INQUIRY",
    "GENERAL_INTELLIGENCE",
    "TECHNICAL",
    "TASK_EXECUTION",
    "REPOSITORY_AUDIT",
    "DEEP_RESEARCH",
    "SYSTEM_DIAGNOSTICS",
)

INDONESIAN_NORMALIZATION_MAP: dict[str, str] = {
    "sofwer": "software",
    "sofware": "software",
    "softer": "software",
    "softwer": "software",
    "softwere": "software",
    "sofwere": "software",
    "softwar": "software",
    "perangkat lunak": "software",
    "penegmbangan": "pengembangan",
    "poengembangan": "pengembangan",
    "pengembagan": "pengembangan",
    "pengmbangan": "pengembangan",
    "pengambangan": "pengembangan",
    "pemgembangan": "pengembangan",
    "mengembangkan": "pengembangan",
    "kembangkan": "pengembangan",
    "koding": "coding",
    "pemrograman": "coding",
    "pemograman": "coding",
    "repositori": "repository",
    "repo": "repository",
    "periksa": "cek",
    "diagnosa": "diagnostik",
    "instruksi": "opcode",
    "prosesor": "hcpu",
    "papan": "board",
}

FOLLOWUP_PHRASES: tuple[str, ...] = (
    "jelaskan lebih detail",
    "jelaskan lebih lanjut",
    "lebih detail",
    "bagaimana cara kerjanya",
    "cara kerjanya",
    "hubungannya dengan",
    "pertanyaan tadi",
    "pembahasan sebelumnya",
    "lanjutkan pembahasan",
    "lanjutkan yang tadi",
    "mengontrol keduanya",
    "itu bekerja",
    "lihat ringkasan",
    "tampilkan ringkasan",
    "ya, tampilkan",
    "contohnya",
    "contohnya apa",
    "berikan contoh",
    "kasih contoh",
    "maksudnya",
    "maksudnya gimana",
)

# Explicit keywords that indicate a query is about the CosmicTera repository/hardware/math ecosystem
COSMICTERA_DOMAIN_KEYWORDS: tuple[str, ...] = (
    "cosmictera",
    "hijaiyyah",
    "hybit",
    "18d",
    "hcpu",
    "h-isa",
    "hisa",
    "hasm",
    "hbc",
    "hcc",
    "hvm",
    "hcvm",
    "hisab",
    "har",
    "hpg",
    "hos",
    "hfs",
    "hmcl",
    "kabah",
    "ka'bah",
    "jamrah",
    "usss",
    "six-guard",
    "six guard",
    "master_table",
    "master table",
    "exomatrix",
    "eksomatriks",
    "bsm",
    "basmalah",
    "tang nano",
    "gowin",
    "openfpgaloader",
    "fpga",
    "verilog",
    "rtl",
    "watchdog",
    "clock drift",
    "tier1_clock_drift",
    "no_watchdog_exists",
    "burn-in",
    "burnin",
    "hanyut",
    "repository",
    "repositori",
    "repo",
    "cek sistem",
    "status sistem",
    "kondisi sistem",
    "lapis 0",
    "lapis 1",
    "lapis 2",
    "lapis 3",
    "lapis 4",
    "lapis 5",
    "lapis 6",
    "lapis 7",
    "lapis 8",
    "lapis 9",
    "lapis 10",
    "lapis 11",
    "layer 0",
    "layer 6",
    "layer 7",
    "l0",
    "l6",
    "l7",
    "l9",
    "l11",
    "opcode",
    "hnrm2",
    "hdist",
    "hdot",
    "hload",
    "hcadd",
    "hgrd",
    "test_bsm",
    "ukur ",
    "portal",
    "portal8888",
    "portal 8888",
    "8888",
    "layer7_portal",
    "hijaiyyah_portal8888",
    "jim_sync",
    "jim_index",
    "ingress_parse",
    "find my",
    "findmy",
)


def has_word_boundary_match(term: str, text: str) -> bool:
    """Return True only when `term` matches as a complete word/token in `text` (never a mid-word substring)."""
    t_clean = term.strip()
    if not t_clean or not text:
        return False
    pattern = rf"(?<![a-zA-Z0-9_\u0600-\u06FF]){re.escape(t_clean)}(?![a-zA-Z0-9_\u0600-\u06FF])"
    return bool(re.search(pattern, text, flags=re.IGNORECASE))


def normalize_indonesian_query(text: str) -> str:
    """Normalize common Indonesian spellings and colloquial variants while preserving technical identifiers."""
    out = text.strip()
    for src, dst in INDONESIAN_NORMALIZATION_MAP.items():
        out = re.sub(
            rf"(?<![a-zA-Z0-9_]){re.escape(src)}(?![a-zA-Z0-9_])",
            dst,
            out,
            flags=re.IGNORECASE,
        )
    return out


def normalize_indonesian_token(token: str) -> str:
    """Normalize an individual token, mapping synonyms and stripping conversational suffixes when safe."""
    t_low = token.strip().lower()
    if t_low in INDONESIAN_NORMALIZATION_MAP:
        return INDONESIAN_NORMALIZATION_MAP[t_low]
    for suffix in ("nya", "lah", "kah"):
        if t_low.endswith(suffix) and len(t_low) - len(suffix) >= 4:
            stem = t_low[: -len(suffix)]
            return INDONESIAN_NORMALIZATION_MAP.get(stem, stem)
    return t_low


GENERIC_NON_REPO_WORDS: set[str] = {
    "def", "float", "int", "str", "bool", "list", "dict", "set", "tuple", "return",
    "class", "import", "from", "async", "await", "hitung", "luas", "persegi", "sisi",
    "beserta", "penggunaannya", "monolith", "microservices", "arsitektur", "secara",
    "singkat", "perbedaan", "jelaskan", "buat", "buatkan", "fungsi", "python", "javascript",
    "typescript", "swift", "rust", "html", "css", "sql", "server", "client", "api",
    "rest", "graphql", "rencana", "langkah", "menyelesaikan", "presisi", "implementasi",
    "penjelasan", "teknis", "lengkap", "akurat", "tinjau", "solusi", "poin", "aman",
    "benar", "kode", "contoh", "aplikasi", "software", "pengembangan", "membantu",
    "kamu", "bisa", "halo", "hai", "siapa", "test", "tests", "src", "docs", "build",
    "data", "core", "model", "models", "main", "init", "utils", "config", "index",
}


def extract_workspace_search_terms(query_text: str) -> list[str]:
    """Extract specific folder/file identifiers and space-collapsed compound tokens (e.g. 'Portal 8888' -> 'portal8888') while ignoring generic programming words."""
    q_lower = normalize_indonesian_query(query_text.strip().lower())
    raw_words = [
        w
        for w in re.findall(r"[a-z0-9_\-]{2,}", q_lower)
        if w not in NUIContextualRetriever.STOPWORDS and w not in GENERIC_NON_REPO_WORDS
    ]
    terms: list[str] = []
    for w in raw_words:
        if len(w) >= 4 and w not in terms:
            terms.append(w)
    all_words = [
        w for w in re.findall(r"[a-z0-9_\-]{2,}", q_lower)
        if w not in NUIContextualRetriever.STOPWORDS
    ]
    for i in range(len(all_words) - 1):
        w1, w2 = all_words[i], all_words[i + 1]
        if w1 in GENERIC_NON_REPO_WORDS and w2 in GENERIC_NON_REPO_WORDS:
            continue
        joined = w1 + w2
        under = w1 + "_" + w2
        for cand in (joined, under):
            if len(cand) >= 5 and cand not in terms:
                terms.append(cand)
    return terms


def scan_workspace_for_query(
    query_text: str,
    repo_root: Path = REPO_ROOT,
    extra_folders: list[str] | None = None,
) -> dict[str, Any]:
    """Dynamically scan REPO_ROOT and active Connected Folders for directories and files matching the query (including space-collapsed names like 'portal8888')."""
    terms = extract_workspace_search_terms(query_text)
    if not terms:
        return {"matched_dirs": [], "matched_files": [], "summary_markdown": ""}

    skip_dirs = {
        ".git",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".build",
        "DerivedData",
    }
    roots: list[Path] = [repo_root]
    for ef in (extra_folders if extra_folders is not None else ["/Users/AMRA/opt"]):
        p_ef = Path(ef)
        try:
            _exists = p_ef.exists()
        except OSError:
            _exists = False
        if _exists and p_ef not in roots:
            roots.append(p_ef)

    matched_dirs: list[Path] = []
    matched_files: list[tuple[int, Path]] = []

    for root_p in roots:
        try:
            for top_entry in sorted(root_p.iterdir(), key=lambda x: x.name.lower()):
                if top_entry.name in skip_dirs or top_entry.name.startswith("."):
                    continue
                name_low = top_entry.name.lower()
                name_alnum = re.sub(r"[^a-z0-9]", "", name_low)
                if top_entry.is_dir():
                    if any(
                        t == name_low
                        or t == name_alnum
                        or (len(t) >= 4 and t in name_low)
                        for t in terms
                    ):
                        if top_entry not in matched_dirs:
                            matched_dirs.append(top_entry)
                    for sub_p in top_entry.rglob("*"):
                        if any(
                            part in skip_dirs or part.startswith(".")
                            for part in sub_p.parts
                        ):
                            continue
                        try:
                            rel_parts = sub_p.relative_to(root_p).parts
                            if len(rel_parts) > 4:
                                continue
                        except Exception:
                            continue
                        sub_low = sub_p.name.lower()
                        sub_alnum = re.sub(r"[^a-z0-9]", "", sub_low)
                        score = sum(
                            4 if (t == sub_alnum or t == sub_low) else (2 if t in sub_low else 0)
                            for t in terms
                            if len(t) >= 3
                        )
                        if score > 0:
                            if sub_p.is_dir() and sub_p not in matched_dirs:
                                matched_dirs.append(sub_p)
                            elif sub_p.is_file():
                                matched_files.append((score, sub_p))
                elif top_entry.is_file():
                    score = sum(
                        4 if (t == name_alnum or t == name_low) else (2 if t in name_low else 0)
                        for t in terms
                        if len(t) >= 3
                    )
                    if score > 0:
                        matched_files.append((score, top_entry))
        except Exception:
            continue

    matched_files.sort(key=lambda x: (-x[0], str(x[1])))
    top_files = [fp for _, fp in matched_files[:20]]

    md_lines: list[str] = []
    for d_path in matched_dirs[:4]:
        try:
            rel_d = (
                str(d_path.relative_to(repo_root))
                if d_path.is_relative_to(repo_root)
                else str(d_path)
            )
        except Exception:
            rel_d = str(d_path)
        dir_files: list[str] = []
        for f_in in sorted(d_path.rglob("*")):
            if f_in.is_file() and not any(
                pt in skip_dirs or pt.startswith(".") for pt in f_in.parts
            ):
                try:
                    dir_files.append(
                        str(f_in.relative_to(repo_root))
                        if f_in.is_relative_to(repo_root)
                        else str(f_in)
                    )
                except Exception:
                    dir_files.append(str(f_in))
        md_lines.append(
            f"- **Folder Aktual Ditemukan di Repo**: `{rel_d}/` ({len(dir_files)} berkas): "
            + ", ".join(f"`{df}`" for df in dir_files[:20])
        )
        for doc_cand in ("README.md", "ARCHITECTURE.md", "sim/EVIDENCE.md"):
            doc_p = d_path / doc_cand
            if doc_p.is_file():
                try:
                    snippet = doc_p.read_text(encoding="utf-8", errors="replace")[:1800].strip()
                    md_lines.append(
                        f"- **Isi Dokumen Resmi (`{rel_d}/{doc_cand}`)**:\n{snippet}"
                    )
                except Exception:
                    pass

    if top_files:
        rel_top = []
        for fp in top_files[:12]:
            try:
                rel_top.append(
                    str(fp.relative_to(repo_root))
                    if fp.is_relative_to(repo_root)
                    else str(fp)
                )
            except Exception:
                rel_top.append(str(fp))
        md_lines.append(
            "- **Berkas Terkait yang Ditemukan di Repo**: "
            + ", ".join(f"`{rt}`" for rt in rel_top)
        )

    return {
        "matched_dirs": [str(d) for d in matched_dirs[:6]],
        "matched_files": [str(f) for f in top_files[:20]],
        "summary_markdown": "\n\n".join(md_lines),
    }


def is_cosmictera_domain_query(query_text: str) -> bool:
    """Return True ONLY if the query is specifically about CosmicTera, Hijaiyyah Mathematics, HCPU, H-ISA, FPGA, or matches a real folder/file in the repository."""
    q_clean = query_text.strip()
    q_lower = q_clean.lower()
    q_norm = normalize_indonesian_query(q_lower)

    for kw in COSMICTERA_DOMAIN_KEYWORDS:
        if " " in kw or "-" in kw or "." in kw:
            if kw in q_lower or kw in q_norm:
                return True
        elif has_word_boundary_match(kw, q_lower) or has_word_boundary_match(kw, q_norm):
            return True

    if has_word_boundary_match("huruf", q_lower) or any(
        e.char in q_clean for e in MASTER_TABLE.all_entries()
    ):
        for entry in MASTER_TABLE.all_entries():
            if entry.char in q_clean or has_word_boundary_match(entry.name.lower(), q_lower):
                return True

    if any(w in q_lower or w in q_norm for w in ("cek", "periksa", "folder", "berkas", "file", "modul", "portal", "8888", "layer", "lapis", "buku")):
        ws_hit = scan_workspace_for_query(q_clean)
        if ws_hit["matched_dirs"] or ws_hit["matched_files"]:
            return True

    return False


def classify_capability_subintent(q_lower: str, q_norm: str) -> str | None:
    """Detect if the user is asking about NUI's capabilities (software dev, coding, languages, bug fixing, web, repo access)."""
    # Do NOT classify as capability inquiry if user is giving a concrete code-generation, explanation, or system command
    if any(
        cmd in q_lower or cmd in q_norm
        for cmd in (
            "buatkan ",
            "buatlah ",
            "buat contoh",
            "tuliskan ",
            "tulis kode",
            "jelaskan perbedaan",
            "jelaskan hubungan",
            "jelaskan watchdog",
            "apa fungsi repository",
            "apa fungsi repositori",
            "fungsi repository",
            "fungsi repositori",
            "bagaimana cara membuat website",
            "cara membuat website",
            "bantu saya mencari bug",
            "mencari bug dalam kode",
            "cari bug",
            "hitung ",
            "berapa ",
            "jalankan program",
            "cek sistem",
            "cek status sistem",
            "status sistem",
            "cek repository",
            "periksa repository",
            "clock drift",
        )
    ):
        return None

    # 1. Repository reading / inspection capability ("Apakah kamu bisa membaca repository CosmicTera?")
    if (
        any(w in q_lower or w in q_norm for w in ("repository", "repositori", "repo"))
        and any(
            w in q_lower
            for w in (
                "bisa",
                "apakah",
                "dapat",
                "mampu",
                "membaca",
                "baca",
                "mengakses",
                "akses",
                "memahami",
            )
        )
    ):
        return "repository_reading_capability"

    # 2. Programming languages supported ("Bahasa pemrograman apa yang bisa kamu bantu?")
    if "bahasa" in q_lower and any(
        w in q_lower or w in q_norm
        for w in ("pemrograman", "coding", "kode", "bisa", "bantu", "dukung", "apa saja", "apa yang")
    ):
        return "programming_languages_capability"

    # 3. Website creation capability ("Bisa membuat website?", "Kamu bisa bikin web?")
    if (
        any(w in q_lower for w in ("website", "web", "halaman web", "frontend", "aplikasi web"))
        and any(w in q_lower for w in ("bisa", "dapat", "mampu", "apakah"))
        and not any(w in q_lower for w in ("bagaimana cara", "gimana cara", "langkah", "tutorial", "dari nol"))
    ):
        return "website_development_capability"

    # 4. Bug fixing / debugging capability ("Bisa memperbaiki bug Python?", "Bisa debug kode?")
    if (
        any(w in q_lower for w in ("bug", "error", "debug", "debugging", "memperbaiki", "perbaiki"))
        and any(w in q_lower for w in ("bisa", "dapat", "mampu", "apakah"))
        and "kode ini" not in q_lower
    ):
        return "python_debugging_capability"

    # 5. How NUI codes / coding workflow ("Bagaimana cara kamu coding?", "Cara kamu coding gimana?")
    if any(
        phrase in q_lower or phrase in q_norm
        for phrase in (
            "cara kamu coding",
            "cara nui coding",
            "bagaimana cara kamu coding",
            "bagaimana kamu coding",
            "gimana kamu coding",
            "gimana cara kamu coding",
            "cara kerja coding",
        )
    ):
        return "coding_workflow_capability"

    # 6. General software development & program design capability
    # ("Kamu bisa membantu pengembangan software?", "Kamu bisa membantu penegmbangan softer ?", "kamu bisa bantu poengembangan sofwer")
    if any(
        phrase in q_lower or phrase in q_norm
        for phrase in (
            "pengembangan software",
            "membantu pengembangan",
            "bantu pengembangan",
            "mengembangkan software",
            "rancangan program",
            "merancang program",
            "bisa coding",
            "kemampuan coding",
            "bisa bantu coding",
            "membantu coding",
            "kamu bisa membantu",
            "kamu bisa bantu",
            "apakah kamu bisa membantu",
            "apakah kamu bisa bantu",
            "bisa membantu pengembangan",
            "bisa bantu pengembangan",
        )
    ) or (
        any(
            w in q_lower or w in q_norm
            for w in (
                "software",
                "softer",
                "sofwer",
                "aplikasi",
                "program",
                "pengembangan",
                "penegmbangan",
                "poengembangan",
            )
        )
        and any(
            w in q_lower or w in q_norm
            for w in ("bisa", "bis", "membantu", "bantu", "pengembangan", "rancangan", "merancang")
        )
    ):
        return "software_development_capability"

    # 7. General task/capability inquiry ("Apa saja tugas kamu?", "Kamu bisa apa saja?")
    if any(
        phrase in q_lower
        for phrase in (
            "apa saja tugas kamu",
            "tugas kamu apa",
            "kamu bisa apa",
            "apa yang bisa kamu lakukan",
            "kemampuan kamu apa",
        )
    ):
        return "general_nui_capability"

    return None


def classify_response_mode(
    query_text: str,
    conversation_context: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Classify the user prompt into one of the response modes to control intent routing, retrieval, and answer style."""
    q_clean = query_text.strip()
    q_lower = q_clean.lower()
    q_norm = normalize_indonesian_query(q_lower)
    history = list(conversation_context or [])
    prior_assistant_msgs = [
        m for m in history if m.get("role") == "assistant" and str(m.get("content", "")).strip()
    ]
    prior_user_msgs = [
        m
        for m in history
        if m.get("role") == "user"
        and str(m.get("content", "")).strip()
        and str(m.get("content", "")).strip() != q_clean
    ]
    already_greeted = len(prior_assistant_msgs) > 0
    last_user_topic = str(prior_user_msgs[-1]["content"]).strip() if prior_user_msgs else ""
    last_assistant_reply = (
        str(prior_assistant_msgs[-1]["content"]).strip() if prior_assistant_msgs else ""
    )

    # 1. Capability Inquiry ("Kamu bisa membantu pengembangan software?", "Bagaimana cara kamu coding?", etc.)
    cap_subintent = classify_capability_subintent(q_lower, q_norm)
    if cap_subintent is not None:
        return {
            "mode": "CAPABILITY_INQUIRY",
            "sub_intent": cap_subintent,
            "is_cosmictera_specific": cap_subintent == "repository_reading_capability",
            "max_paragraphs": 3,
            "include_sources": False,
            "already_greeted": already_greeted,
            "is_followup": False,
            "last_user_topic": last_user_topic,
            "last_assistant_reply": last_assistant_reply[:400],
            "guidance": (
                "Jawab secara alami dan langsung mengenai kemampuan nyata NUI (analisis kode, perancangan program, "
                "penulisan/perbaikan kode, unit test pytest, debugging, website, dan akses repository sesuai izin) "
                "tanpa mengambil fakta hardware/burnin yang tidak relevan."
            ),
        }

    is_followup = bool(prior_user_msgs or prior_assistant_msgs) and (
        any(phrase in q_lower or phrase in q_norm for phrase in FOLLOWUP_PHRASES)
        or q_lower in {"contohnya?", "contohnya", "maksudnya?", "maksudnya", "lanjutkan", "lanjutkan."}
    )

    # 2. Explicit full audit / deep report request -> DEEP_RESEARCH
    if any(
        phrase in q_lower
        for phrase in (
            "tampilkan seluruh hasil audit",
            "seluruh hasil audit",
            "laporan lengkap",
            "tampilkan semua hasil",
            "berikan detail lengkap",
            "full audit",
            "deep research",
        )
    ):
        return {
            "mode": "DEEP_RESEARCH",
            "sub_intent": "full_audit_report",
            "is_cosmictera_specific": True,
            "max_paragraphs": 10,
            "include_sources": True,
            "already_greeted": already_greeted,
            "is_followup": is_followup,
            "last_user_topic": last_user_topic,
            "guidance": "Berikan laporan lengkap, terstruktur, dan komprehensif beserta referensi berkas dan hasil verifikasi.",
        }

    # 3. Explicit system diagnostics / connection health inquiry -> SYSTEM_DIAGNOSTICS
    if any(
        phrase in q_lower or phrase in q_norm
        for phrase in (
            "cek sistem",
            "cek status sistem",
            "periksa sistem",
            "diagnosa sistem",
            "diagnostik sistem",
            "system check",
            "system diagnostics",
            "cek kondisi sistem",
            "apakah nui aktif",
            "status koneksi",
            "status sistem",
            "koneksi sistem",
            "health check",
            "cek layanan",
            "status provider",
            "status hardware",
            "status ollama",
            "status nui",
        )
    ):
        return {
            "mode": "SYSTEM_DIAGNOSTICS",
            "sub_intent": "system_health_check",
            "is_cosmictera_specific": True,
            "max_paragraphs": 3,
            "include_sources": False,
            "already_greeted": already_greeted,
            "is_followup": is_followup,
            "last_user_topic": last_user_topic,
            "guidance": "Jalankan pemeriksaan sistem read-only dan tampilkan status aktual layanan lokal, provider, model, memori, dan perangkat keras secara akurat.",
        }

    # 4. Repository check / inspection / recent work / Git history / folder action request -> REPOSITORY_AUDIT
    is_recent_repo_work = any(
        phrase in q_lower or phrase in q_norm
        for phrase in (
            "pekerjaan terakhir",
            "pekerjaan terbaru",
            "perubahan terakhir",
            "perubahan terbaru",
            "commit terakhir",
            "commit terbaru",
            "riwayat pekerjaan",
            "riwayat git",
            "riwayat commit",
            "riwayat repository",
            "riwayat repositori",
            "git log",
            "git status",
            "git diff",
            "file terbaru",
            "file terakhir",
            "berkas terbaru",
            "berkas terakhir",
            "apa yang terakhir dikerjakan",
            "apa yang baru dikerjakan",
            "update terakhir",
            "update terbaru",
            "aktivitas terakhir",
        )
    )
    if is_recent_repo_work or any(
        phrase in q_lower or phrase in q_norm
        for phrase in (
            "cek repository",
            "cek repositori",
            "cek repo",
            "periksa repository",
            "periksa repositori",
            "audit repository",
            "audit repositori",
            "check repository",
            "status repository",
            "status repositori",
            "kondisi repository",
            "apa fungsi repository cosmictera",
            "apa fungsi repositori cosmictera",
            "fungsi repository cosmictera",
            "fungsi repositori cosmictera",
            "cek folder",
            "isi folder",
            "daftar folder",
            "folder terhubung",
            "connected folder",
        )
    ):
        sub_intent = "repository_inspection"
        if "fungsi" in q_lower and ("repository" in q_norm or "cosmictera" in q_lower):
            sub_intent = "repository_purpose"
        elif is_recent_repo_work or any(w in q_lower for w in ("terakhir", "terbaru", "git", "diff", "commit", "folder")):
            sub_intent = "recent_work_and_git"
        return {
            "mode": "REPOSITORY_AUDIT",
            "sub_intent": sub_intent,
            "is_cosmictera_specific": True,
            "max_paragraphs": 6,
            "include_sources": True,
            "already_greeted": already_greeted,
            "is_followup": is_followup,
            "last_user_topic": last_user_topic,
            "guidance": (
                "Sampaikan langsung hasil pemeriksaan aktual dari Git (`git log`, `git status`, `git diff`), "
                "daftar file yang terakhir diubah pada disk, serta Connected Folders yang terhubung. "
                "JANGAN PERNAH menjawab bahwa Anda tidak memiliki akses ke Git atau repository lokal."
            ),
        }

    # 5. Follow-up questions in an active multi-turn conversation
    if is_followup:
        followup_is_ct = is_cosmictera_domain_query(f"{last_user_topic} {q_clean}")
        return {
            "mode": "TECHNICAL" if followup_is_ct else "GENERAL_INTELLIGENCE",
            "sub_intent": "contextual_followup",
            "is_cosmictera_specific": followup_is_ct,
            "max_paragraphs": 4,
            "include_sources": followup_is_ct,
            "already_greeted": already_greeted,
            "is_followup": True,
            "last_user_topic": last_user_topic,
            "last_assistant_reply": last_assistant_reply[:400],
            "guidance": (
                "Ini adalah pertanyaan lanjutan dari percakapan sebelumnya. Hubungkan langsung jawaban Anda "
                "dengan topik yang baru saja dibahas tanpa mengulang salam atau perkenalan diri."
            ),
        }

    # 6. Simple greetings, identity questions, or simple arithmetic -> CONVERSATIONAL
    is_pure_greeting = bool(
        re.match(
            r"^(hai|halo|hello|hi|selamat\s+(pagi|siang|sore|malam))(\s+nui)?[\.\!\?]*$",
            q_lower,
        )
    )
    is_identity_question = any(
        phrase in q_lower
        for phrase in ("kamu siapa", "siapa kamu", "who are you", "perkenalkan dirimu")
    )
    is_simple_math = bool(
        re.search(r"(-?\d+)\s*(\+|\-|\*|x|×|/)\s*(-?\d+)", q_clean)
    ) and not any(w in q_lower for w in ("jelaskan", "rincian", "detail", "bagaimana"))

    if is_pure_greeting or is_identity_question or is_simple_math:
        return {
            "mode": "CONVERSATIONAL",
            "sub_intent": "direct_conversation",
            "is_cosmictera_specific": False,
            "max_paragraphs": 2,
            "include_sources": False,
            "already_greeted": already_greeted,
            "is_followup": False,
            "last_user_topic": last_user_topic,
            "guidance": (
                "Jawab secara alami, singkat, dan langsung ke inti "
                "tanpa menampilkan status sistem atau daftar fakta mentah."
            ),
        }

    # 7. Check whether the query is CosmicTera-specific or General AI / Coding / CS
    is_ct = is_cosmictera_domain_query(q_clean)
    if not is_ct:
        return {
            "mode": "GENERAL_INTELLIGENCE",
            "sub_intent": "general_coding_or_knowledge",
            "is_cosmictera_specific": False,
            "max_paragraphs": 6,
            "include_sources": False,
            "already_greeted": already_greeted,
            "is_followup": False,
            "last_user_topic": last_user_topic,
            "guidance": (
                "Ini adalah pertanyaan pemrograman umum, ilmu komputer, atau pengetahuan umum. "
                "Jawab secara lengkap, cerdas, dan terstruktur menggunakan kemampuan penuh Local LLM "
                "tanpa menyisipkan fakta hardware CosmicTera yang tidak ditanyakan."
            ),
        }

    # 8. CosmicTera task execution or technical domain inquiry -> TECHNICAL / TASK_EXECUTION
    is_hc_or_hasm = (
        ("let " in q_lower and ("print(" in q_lower or "println(" in q_lower))
        or any(tok in q_clean.upper() for tok in ("MOVI ", "HLOAD ", "HNRM2 ", "HDIST ", "HDOT ", "HGRD "))
        or "test_bsm.hasm" in q_lower
        or any(
            p in q_lower or p in q_norm
            for p in ("jalankan program h-isa", "jalankan program hisa", "eksekusi program h-isa")
        )
    )
    if is_hc_or_hasm:
        return {
            "mode": "TASK_EXECUTION",
            "sub_intent": "task_or_code_execution",
            "is_cosmictera_specific": True,
            "max_paragraphs": 4,
            "include_sources": True,
            "already_greeted": already_greeted,
            "is_followup": is_followup,
            "last_user_topic": last_user_topic,
            "guidance": "Jalankan program/perhitungan H-ISA pada HISAMachine dan sampaikan hasil aktualnya.",
        }

    return {
        "mode": "TECHNICAL",
        "sub_intent": "cosmictera_or_technical_inquiry",
        "is_cosmictera_specific": True,
        "max_paragraphs": 5,
        "include_sources": True,
        "already_greeted": already_greeted,
        "is_followup": is_followup,
        "last_user_topic": last_user_topic,
        "guidance": (
            "Berikan jawaban teknis CosmicTera yang akurat berdasarkan konteks repositori yang terverifikasi "
            "tanpa menyalin potongan dokumen mentah yang tidak diminta."
        ),
    }


def strip_internal_thinking(text: str) -> tuple[str, bool]:
    """Remove any `<think>...</think>` or `<thinking>...</thinking>` blocks from model text."""
    if not text:
        return ("", False)
    had_thinking = False
    cleaned = text
    for pattern in (
        r"<think>.*?</think>",
        r"<thinking>.*?</thinking>",
        r"<think>.*$",
        r"<thinking>.*$",
    ):
        if re.search(pattern, cleaned, flags=re.DOTALL | re.IGNORECASE):
            had_thinking = True
            cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    return (cleaned.strip() if had_thinking else cleaned, had_thinking)


@dataclass(frozen=True)
class RetrievedContextSource:
    file_path: str
    title: str
    section: str
    relevance_score: float
    git_commit: str
    epistemic_class: str  # "REPOSITORY_FACT", "SOURCE_CODE", "DOCUMENTATION", "KNOWLEDGE_L9_7DOMAIN", "USR_SEMANTIC_PARSE"
    excerpt: str


class NUIPersonaLoader:
    """Loads and reconciles the official CosmicTera NUI persona and system instructions from repository files."""

    PERSONA_SOURCES: tuple[str, ...] = (
        "src/hijaiyyah/ai/runtime.py",
        "AGENTS.md",
        "cosmictera/RULES.md",
        "NUI/LAYERS.md",
        "NUI/LAYER8.md",
        "NUI/LAYER9.md",
        "NUI/LAYER10.md",
        "NUI/LAYER11.md",
        "teknologi/ISTILAH.md",
    )

    def __init__(self, repo_root: Path = REPO_ROOT) -> None:
        self.repo_root = repo_root

    def get_git_head_short(self) -> str:
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            return res.stdout.strip() or "920f3e61"
        except Exception:
            return "920f3e61"

    def load_official_persona_metadata(self) -> dict[str, Any]:
        """Inspect and return the exact repository persona sources and checksums."""
        prog = HybitAIProgram()
        source_hashes: dict[str, str] = {}
        for rel in self.PERSONA_SOURCES:
            p = self.repo_root / rel
            if p.is_file():
                source_hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        return {
            "identity_name": "NUI (Natural Universal Intelligence) — CosmicTera",
            "canonical_persona_source": "src/hijaiyyah/ai/runtime.py (HybitAIProgram.system)",
            "canonical_system_prompt": prog.system,
            "reconciled_sources": list(self.PERSONA_SOURCES),
            "source_sha256_prefixes": source_hashes,
            "git_commit": self.get_git_head_short(),
            "architecture_mapping": [
                {"component": "NUI Persona", "function": "Identitas dan karakter resmi NUI dari src/hijaiyyah/ai/runtime.py & NUI/LAYERS.md"},
                {"component": "NUI System Prompt", "function": "Instruksi utama dan aturan perilaku epistemik (AGENTS.md K1-K15, cosmictera/RULES.md R1-R13)"},
                {"component": "NUI Thinking Framework", "function": "Siklus 7 tahap (INPUT -> UNDERSTANDING -> COORDINATION -> EXECUTION -> MONITORING -> DECISION -> FEEDBACK) lintas L0-L11"},
                {"component": "NUI Context", "function": "Konteks pengguna, sesi multi-giliran, knowledge.query(), usr.parse_phrase(), dan NUIContextualRetriever"},
                {"component": "NUI Orchestrator", "function": "Pengaturan alur tugas, routing model/deterministik, dan validasi hasil (orchestrator.py)"},
                {"component": "NUI Tool Registry", "function": "Kemampuan terintegrasi: File, Coding, Git, Terminal, Web/Browser, API, Hardware, CosmicTera Subsystems (tools.py)"},
                {"component": "NUI Permission Engine", "function": "Pengendalian otorisasi 15 kategori & 6 mode persetujuan (permissions.py)"},
                {"component": "Ollama", "function": "Local Language Model Inference & Coding Intelligence Asset (127.0.0.1:11434)"},
                {"component": "NUI Desktop", "function": "Antarmuka native macOS SwiftUI + AppKit + WebKit (CosmicTera NUI.app)"},
            ],
        }

    def build_system_prompt(
        self,
        *,
        retrieved_sources: list[RetrievedContextSource] | None = None,
        operating_mode: str = "HYBRID",
        active_model_role: str = "GENERAL_AND_CODING",
        session_summary: str | None = None,
        response_mode_info: dict[str, Any] | None = None,
        deterministic_context: str | None = None,
    ) -> str:
        """Construct the System Prompt combining Official NUI Identity (`HybitAIProgram.system`) with unrestricted General & Coding Intelligence."""
        prog = HybitAIProgram()
        commit_id = self.get_git_head_short()
        mode_info = response_mode_info or {
            "mode": "GENERAL_INTELLIGENCE",
            "already_greeted": False,
            "is_cosmictera_specific": False,
            "guidance": "Jawab secara alami, cerdas, dan langsung sesuai pertanyaan.",
        }
        r_mode = mode_info.get("mode", "GENERAL_INTELLIGENCE")
        already_greeted = bool(mode_info.get("already_greeted", False))
        is_followup = bool(mode_info.get("is_followup", False))
        is_ct_specific = bool(mode_info.get("is_cosmictera_specific", False))
        last_user_topic = str(mode_info.get("last_user_topic", "")).strip()
        last_assistant_reply = str(mode_info.get("last_assistant_reply", "")).strip()
        mode_guidance = mode_info.get("guidance", "")

        sections: list[str] = [
            # 1. Identitas Resmi CosmicTera NUI
            "=== [1. IDENTITAS RESMI COSMICTERA NUI] ===\n"
            "Anda adalah NUI (Natural Universal Intelligence), asisten AI cerdas dan pusat komputasi dari ekosistem CosmicTera. "
            "Tetaplah menggunakan identitas NUI dalam setiap percakapan.",
            # 2. System Instructions Resmi NUI (dari src/hijaiyyah/ai/runtime.py) + Penjelasan Cakupan
            f"=== [2. ATURAN INTI NUI (src/hijaiyyah/ai/runtime.py @ {commit_id})] ===\n"
            f"Aturan untuk klaim internal repositori CosmicTera:\n\"{prog.system}\"\n"
            "PENTING — CAKUPAN KECERDASAN UMUM & CODING:\n"
            "- Aturan 'Jawab hanya dari konteks yang diberikan' di atas HANYA berlaku ketika pengguna menanyakan fakta internal perangkat keras/repositori CosmicTera (agar Anda tidak mengarang angka spesifikasi HCPU/FPGA).\n"
            "- Untuk pertanyaan UMUM, pemrograman/pengembangan software (Python, JavaScript, Swift, C/C++, HTML, CSS, Rust, SQL, REST API vs GraphQL, debugging, algoritma, arsitektur aplikasi, website dari nol), analisis, matematika, dan percakapan sehari-hari: Anda WAJIB menjawab secara cerdas, lengkap, dan langsung menggunakan pengetahuan umum dan kemampuan coding Anda sebagai LLM, meskipun topik tersebut tidak ada di dalam repositori CosmicTera.",
            # 3. Aturan Komunikasi Alami & Pembagian Tugas
            "=== [3. GAYA KOMUNIKASI & PEMBAGIAN TUGAS] ===\n"
            f"- Mode Respons Saat Ini: `{r_mode}` ({mode_guidance})\n"
            f"- Status Sapaan Sesi: `{'SUDAH_MENYAPA' if already_greeted else 'BELUM_MENYAPA'}` "
            "(Jika `SUDAH_MENYAPA`, jangan mengulang sapaan 'Halo!' di awal pesan).\n"
            f"- Pertanyaan Lanjutan (Follow-up): `{'YA' if is_followup else 'TIDAK'}` "
            + (f"(Topik sebelumnya: \"{last_user_topic}\").\n" if last_user_topic else "\n")
            + "- Jawab langsung dalam bahasa Indonesia yang alami, jelas, dan membantu.\n"
            "- Jika pengguna meminta contoh kode/aplikasi (misalnya Python, HTML/CSS/JS, REST API), berikan kode yang bersih, lengkap, dan siap dijalankan beserta penjelasan singkat.\n"
            "- Jika pengguna meminta bantuan mencari bug (namun belum melampirkan kodenya), jelaskan langkah-langkah menemukan bug, berikan contoh pola bug umum beserta perbaikannya, dan tawarkan pengguna untuk menempelkan kode yang ingin diperiksa.\n"
            "- JANGAN menampilkan proses berpikir internal (`<think>`) dan JANGAN pernah menyisipkan fakta hardware (`watchdog`, `clock drift`) ke dalam jawaban umum.\n"
            "- KEMAMPUAN OPERASIONAL JARINGAN, DOMAIN & VPS (MACOS BACKEND AKTIF): NUI memiliki mesin operasional nyata (`RealInternetEngine`, `RemoteVPSDevelopmentEngine`, `UniversalFileActionEngine`) yang menggunakan koneksi jaringan backend macOS (`en0`, `socket`, `/usr/bin/dig`, `urllib/TLS`, `/usr/bin/ssh`, `/usr/bin/ssh-keyscan`) untuk mengakses internet secara langsung serta menjalankan pemeriksaan DNS (`A`, `AAAA`, `CNAME`, `NS`, `MX`, `TXT`), HTTP/HTTPS & sertifikat TLS, koneksi SSH/SFTP ke VPS, dan perbandingan manifest SHA-256 berkas lokal vs server. DILARANG KERAS pernah menjawab 'Maaf, saya tidak bisa menghubungkan atau mengakses perangkat atau jaringan eksternal secara langsung', 'Saya adalah asisten AI lokal yang beroperasi dalam sistem terbatas', 'Saya tidak memiliki akses langsung ke internet, VPS', atau menawarkan pembuatan script Python/shell sebagai pengganti pemeriksaan langsung.\n"
            "- ATURAN EPISTEMIK COSMICTERA (`cosmictera/RULES.md`): `VF` = Verified Formally, `CC` = Computationally Confirmed, `DP` = Design Property (properti desain arsitektural sengaja, misalnya tidak adanya watchdog di `rtl/` adalah sifat desain deterministik, BUKAN Dynamic Programming), `EH` = Engineering Hypothesis, `AT` = Aspirational Target.\n"
            "- STATUS LAPISAN NUI L0–L11: Seluruh 12 lapisan NUI (`L0` sampai `L11`, termasuk `L8` Diagnostics, `L9` Deductive Reasoning, `L10` Autonomous Engineering, dan `L11` 11-Junction Universal Computation di `src/hijaiyyah/nui/autonomous/`) telah berstatus `IMPLEMENTED_AND_VERIFIED`.",
        ]

        # 4. Spesialisasi CosmicTera (Hanya relevan bila pertanyaan menyangkut kemampuan NUI atau CosmicTera)
        if is_ct_specific or r_mode in {"CAPABILITY_INQUIRY", "REPOSITORY_AUDIT", "SYSTEM_DIAGNOSTICS", "DEEP_RESEARCH"}:
            sections.append(
                "=== [4. KONTEKS SPESIALISASI EKOSISTEM COSMICTERA] ===\n"
                "- **Fungsi Repository CosmicTera (`/Users/AMRA/hijaiyyah-mathematics`)**: Membangun ekosistem komputasi *from letter to silicon* berbasis **Matematika Hijaiyyah** (28 huruf × vektor **Hybit 18D** pada `MASTER_TABLE` dengan invarian **Six-Guard `G1–G4, T1–T2`**), rantai kompilasi **Hybit Code (`HC → HASM → HBC`)**, prosesor silikon 5-tahap **HCPU (`rtl/hcpu_top.v`)** yang mengeksekusi set instruksi **H-ISA v1.2** di FPGA **Sipeed Tang Nano 20K (`GW2AR-LV18QN88C8/I7`, 27 MHz, HDMI 1280×720@60Hz)**, sistem keamanan **USSS + Ka'bah Sponge + Jamrah**, serta arsitektur kecerdasan **NUI L0–L11** dan aplikasi **CosmicTera NUI Desktop**.\n"
                "- **Hubungan H-ISA dengan HCPU**: **H-ISA (*Hijaiyyah Instruction Set Architecture*)** adalah kontrak/spesifikasi arsitektur set instruksi biner 32-bit (105 opcode spesifikasi, 84 opcode RTL, 74 opcode terbukti paritas P3, termasuk 28 opcode atomik huruf Hijaiyyah `0xE0–0xFB` dan instruksi vektor Codex `HLOAD`, `HCADD`, `HNRM2`, `HDIST`, `HDOT`, `HGRD`), sedangkan **HCPU (*Hijaiyyah Core Processing Unit*)** adalah realisasi perangkat keras mikroprosesor pipeline 5-tahap (`IF → ID → EX → MEM → WB`) dalam Verilog RTL (`rtl/hcpu_top.v`) yang mendekode dan mengeksekusi instruksi H-ISA secara langsung di silikon FPGA maupun disimulasikan secara bit-exact oleh `HISAMachine` (`src/hijaiyyah/hisa/machine.py`).\n"
                "- **Kemampuan Coding & Tools NUI**: NUI mendukung pengembangan software lintas bahasa (Python, Swift, JavaScript/TypeScript, C/C++, HTML/CSS, Rust, SQL, Verilog RTL, H-ISA, Hybit Code) serta memiliki tools terdaftar (`files.list`, `files.read`, `files.write`, `coding.edit`, `coding.run_test`, `git.status`, `git.diff`, `web.search`, `web.preview`, `hardware.status`) yang dikendalikan melalui `PermissionEngine`."
            )

        # 5. Hasil Pre-Komputasi Deterministik / Telemetri Aktual / Git & Connected Folders (jika ada)
        if deterministic_context:
            sections.append(
                "=== [5. DATA AKTUAL & HASIL PEMERIKSAAN TERVERIFIKASI (JARINGAN, DOMAIN, VPS, GIT, REPOSITORY & CONNECTED FOLDERS — WAJIB DIGUNAKAN)] ===\n"
                "PERINTAH WAJIB: Anda MEMILIKI akses langsung secara real-time ke pemeriksaan internet/DNS/TLS, status koneksi SSH/SFTP VPS, perbandingan manifest SHA-256 berkas lokal dan server, sistem kontrol versi Git, riwayat commit, "
                "perubahan berkas terbaru, lampiran berkas (`+`), dan Connected Folders melalui data hasil pemeriksaan NUI di bawah ini.\n"
                "DILARANG KERAS menjawab 'Saya adalah AI lokal dan tidak mempunyai akses internet atau VPS', 'Saya tidak dapat memeriksa atau mengakses riwayat pekerjaan terakhir di repositori Anda', "
                "atau 'saya tidak memiliki akses ke Git'. Sajikan langsung data aktual berikut kepada pengguna:\n"
                f"{deterministic_context}"
            )

        # 6. Informasi Konteks Proyek dari Retrieval (HANYA jika pertanyaan adalah tentang CosmicTera)
        if retrieved_sources and is_ct_specific:
            ctx_blocks = []
            for idx, src in enumerate(retrieved_sources, start=1):
                ctx_blocks.append(
                    f"[{idx}] File: `{src.file_path}` | Bagian: {src.section} | Kelas: {src.epistemic_class}\n"
                    f"{src.excerpt}"
                )
            sections.append(
                "=== [6. REFERENSI REPOSITORY COSMICTERA YANG RELEVAN] ===\n"
                + "\n\n".join(ctx_blocks)
            )

        # 7. Ringkasan Memori & Konteks Percakapan Sesi
        if session_summary or last_user_topic or last_assistant_reply:
            mem_lines: list[str] = []
            if session_summary:
                mem_lines.append(session_summary)
            if last_user_topic:
                mem_lines.append(f"- Pesan pengguna sebelumnya: \"{last_user_topic}\"")
            if last_assistant_reply:
                mem_lines.append(f"- Jawaban NUI sebelumnya: \"{last_assistant_reply[:300]}\"")
            sections.append(
                "=== [7. KONTEKS PERCAKAPAN AKTIF & RIWAYAT SESI] ===\n"
                + "\n".join(mem_lines)
            )

        return "\n\n".join(sections)


class NUIContextualRetriever:
    """Retrieves relevant CosmicTera structured knowledge (`knowledge.py`, `usr.py`), documentation, and verified facts ONLY when the query is about CosmicTera."""

    INDEXED_DOCUMENTS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
        ("NUI/LAYERS.md", "Peta Resmi 12 Lapisan NUI (L0–L11)", ("nui", "layer", "lapis", "l0", "l1", "l2", "l3", "l4", "l5", "l6", "l7", "l8", "l9", "l10", "l11", "usr", "ubuntu", "lima")),
        ("teknologi/ISTILAH.md", "Glosarium Resmi Istilah CosmicTera", ("hybit", "hcpu", "h-isa", "hisa", "hc", "hcc", "hasm", "hbc", "hvm", "hisab", "har", "hos", "hfs", "hgss", "hom", "csgi", "istilah")),
        ("docs/HISA_SPEC.md", "Spesifikasi Arsitektur Set Instruksi H-ISA", ("opcode", "instruksi", "register", "h-isa", "hisa", "movi", "hload", "hcadd", "hnrm2", "hdist", "hdot", "hgrd", "trap", "eret")),
        ("NUI/RTL_FUNCTION.md", "Model Fungsi RTL Lapis 6 (UART, MMIO, RAM, Loader, Pipeline, HCPU)", ("l6", "lapis 6", "rtl_function", "pipeline", "mmio", "uart", "dataram", "loader", "oracle")),
        ("NUI/HARDWARE_STATE.md", "Model Keadaan Hardware Lapis 6.4 (IDENTITY, CAPABILITY, OBSERVED, CURRENT)", ("hardware", "state", "tang nano", "fpga", "gowin", "current", "observed", "provenance")),
        ("NUI/LAYER7.md", "Kontrak Operasi Otonom Fail-Closed Lapis 7", ("l7", "lapis 7", "otonom", "autonomous", "fail-closed", "decide", "portal", "send_program", "isolate_fault")),
        ("portal8888/README.md", "Portal 8888 — Implementasi v1 Aktif, Modul RTL, Pembungkus Tang Nano 20K & Status Uji", ("portal", "8888", "portal8888", "hijaiyyah_portal8888", "ingress_parse", "jim_sync", "jim_index", "portal_uart", "find my")),
        ("portal8888/ARCHITECTURE.md", "Portal 8888 — Arsitektur Lengkap L0–L5 (Tangkap, Catatan 125B, Segel HMAC, Rantai 4 Sudut, Otorisasi, Find-My)", ("portal", "8888", "portal8888", "find my", "anti-maling", "hmac", "ed25519", "empat sudut", "jangkar", "rollback")),
        ("src/hijaiyyah/nui/layer7_portal.py", "Integrasi NUI Lapis 7 pada Slot Portal 8888 (ISOLATE_FAULT, RESTART_PORTAL, RECOVER_PORTAL)", ("portal", "8888", "portal8888", "layer7_portal", "isolate_fault", "restart_portal", "recover_portal")),
        ("portal8888/rtl/hijaiyyah_portal8888.v", "RTL Top Operasional v1 Portal 8888 (PHY Capture, SHA-256 Replay, HMAC Seal, 4-Corner Chain & Anchor)", ("portal", "8888", "portal8888", "hijaiyyah_portal8888", "sealed_body", "anc_root")),
        ("portal8888/ref/portal_uart.py", "Protokol & Pemeriksa UART Portal 8888 (Encoder & Checker Byte-Exact)", ("portal", "8888", "portal8888", "portal_uart", "uart")),
        ("cosmictera-build/COSMICTERA_NUI_CONTROL_ALL_SYSTEM_REPORT.md", "Laporan NUI Control All System & Timing Post-Route HDMI 86.01 MHz", ("hdmi", "86.01", "pixel_clk", "control all system", "subsistem", "usss")),
        ("cosmictera-build/PHYSICAL_BUTTON_CONTROL_AND_FAULT_RECOVERY_REPORT.md", "Laporan Kendali Tombol Fisik S1/S2 & Fault Recovery", ("s1", "s2", "tombol", "button", "stop", "recovery", "fault", "guard")),
        ("src/hijaiyyah/core/master_table.py", "Tabel Induk 28 Huruf Hijaiyyah × 18 Dimensi", ("huruf", "hijaiyyah", "18d", "master_table", "vektor", "alif", "ba", "jim", "kha", "sin", "mim")),
        ("src/hijaiyyah/core/guards.py", "Implementasi Six-Guard (G1–G4, T1–T2)", ("guard", "six-guard", "g1", "g2", "g3", "g4", "t1", "t2", "invarian")),
        ("src/hijaiyyah/hmcl/nui_benchmark.py", "Benchmark 8-Sumbu NUI & Koherensi Ruang Fitur HMCL", ("hmcl", "benchmark", "coherence", "koherensi", "self-learning", "charter")),
    )

    STOPWORDS: set[str] = {
        "apa", "itu", "yang", "dan", "dengan", "bagaimana", "jelaskan", "tolong",
        "pada", "dari", "untuk", "hai", "halo", "hello", "kamu", "siapa", "saya",
        "anda", "ini", "lebih", "detail", "lanjut", "lanjutkan", "cek", "periksa",
        "cara", "gimana", "bisa", "bis", "dapat", "mampu", "membantu", "bantu",
        "membaca", "baca", "membuat", "bikin", "memperbaiki", "perbaiki",
        "rancangan", "merancang", "contoh", "contohnya", "maksud", "maksudnya",
        "pengembangan", "software", "sofwer", "sofware", "softer", "aplikasi",
        "program", "bahasa", "pemrograman", "coding", "koding", "kode", "website",
        "web", "bug", "python", "sistem", "pembahasan", "sebelumnya", "tadi",
        "buat", "buatkan", "kasih", "lihat", "coba", "apakah", "kenapa", "mengapa",
        "kapan", "dimana", "mana", "jalankan", "eksekusi", "tentang", "fungsi",
        "kerja", "kerjanya", "dalam", "atau", "jika", "kalau", "bila", "akan",
        "sudah", "belum", "ada", "tidak", "bukan", "saja", "tugas", "desain",
        "berapa", "tercatat", "mesin", "jam", "berhenti", "jalan", "lagi",
        "sederhana", "perbedaan", "rest", "api", "graphql", "nol", "mencari",
    }

    CANONICAL_TERMS: tuple[str, ...] = (
        "HCPU", "Hybit", "H-ISA", "HISAB", "HAR", "HOS", "HFS",
        "HC", "HCC", "HASM", "HBC", "HVM", "HOM", "HGSS", "CSGI",
    )

    # Explicit domain trigger keywords required before any `facts/` entry from that domain can be retrieved
    FACT_DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
        "burnin": (
            "burn-in", "burnin", "watchdog", "no_watchdog_exists",
            "clock drift", "tier1_clock_drift", "drift", "hanyut", "ppm",
            "uptime", "tier1_work_accounts_for_the_time",
        ),
        "crypto": ("kabah", "ka'bah", "sponge", "spons", "avalanche", "hmac", "kriptografi"),
        "kabah": ("kabah", "ka'bah", "sponge", "spons", "avalanche", "hmac"),
        "hcpu": ("hcpu", "pipeline", "imem", "dataram", "fmax", "lut4", "gpr"),
        "hisa": ("h-isa", "hisa", "opcode", "jalr", "computed jump"),
        "fpga": ("jamrah", "pulse", "simpul", "33 clock", "tang nano", "gowin"),
        "jamrah": ("jamrah", "pulse", "simpul", "33 clock"),
        "hijrah": ("hijrah", "exomatrix", "eksomatriks", "700"),
        "sdio": ("sdio", "microsd", "kartu sd", "n_cc", "cmd8"),
        "codex": ("codex", "theta", "rho", "master table", "28 huruf"),
        "nui": (
            "atom.py", "exomatrix_embedding", "physics_embedding",
            "tail_one", "invertibilitas", "invertibel", "theta_u_rho",
            "codex_theta_u_rho_sum",
        ),
        "repository": ("data_memory_words", "four_gates", "4.096 kata", "empat gerbang"),
    }

    def __init__(self, repo_root: Path = REPO_ROOT) -> None:
        self.repo_root = repo_root
        self.persona_loader = NUIPersonaLoader(repo_root=repo_root)
        self.active_connected_folders: list[str] = [str(repo_root), "/Users/AMRA/opt"]

    def sync_active_folders(self, folder_paths: list[str]) -> list[str]:
        """Synchronize the active connected folder list used by context retrieval."""
        normalized: list[str] = []
        for fp in folder_paths:
            try:
                norm_p = str(Path(fp).expanduser().resolve())
            except Exception:
                norm_p = str(fp)
            if norm_p not in normalized:
                normalized.append(norm_p)
        self.active_connected_folders = normalized
        return list(self.active_connected_folders)

    def release_folder(self, folder_path: str) -> list[str]:
        """Release a disconnected folder from active context and repository index."""
        try:
            norm_p = str(Path(folder_path).expanduser().resolve())
        except Exception:
            norm_p = str(folder_path)
        self.active_connected_folders = [
            f for f in self.active_connected_folders if f != norm_p and f != str(folder_path)
        ]
        return list(self.active_connected_folders)

    def retrieve_structured_knowledge(
        self, query_text: str, commit_id: str
    ) -> list[RetrievedContextSource]:
        """Bridge user queries directly to `src/hijaiyyah/nui/usr.py::parse_phrase()` and `knowledge.py::query()`."""
        q_clean = query_text.strip()
        q_lower = q_clean.lower()
        q_norm = normalize_indonesian_query(q_lower)
        structured_sources: list[RetrievedContextSource] = []

        # 1. USR Semantic Phrase Parser (`src/hijaiyyah/nui/usr.py::parse_phrase`)
        cleaned_phrase = re.sub(r"[^\w\s\.\-/]", "", q_clean).strip()
        usr_obj, _ = nui_usr.parse_phrase(cleaned_phrase)
        if usr_obj is None and cleaned_phrase != q_norm:
            usr_obj, _ = nui_usr.parse_phrase(re.sub(r"[^\w\s\.\-/]", "", q_norm).strip())
        if usr_obj is not None:
            problems = nui_usr.validate(usr_obj)
            argv, argv_status = nui_usr.to_argv(usr_obj)
            usr_excerpt = (
                f"USR Semantic Representation: `{json.dumps(usr_obj, ensure_ascii=False)}`\n"
                f"Validation: `{'VALID' if not problems else '; '.join(problems)}`\n"
                f"Catalog Resolution: `{argv if argv else argv_status}`"
            )
            structured_sources.append(
                RetrievedContextSource(
                    file_path="src/hijaiyyah/nui/usr.py (NUI/spec/usr.json)",
                    title=f"USR Semantic Parse ({usr_obj.get('ACTION')} {usr_obj.get('OBJECT')})",
                    section="Universal Semantic Representation (Lapis Semantik)",
                    relevance_score=11.0,
                    git_commit=commit_id,
                    epistemic_class="USR_SEMANTIC_PARSE",
                    excerpt=usr_excerpt,
                )
            )

        # 2. Structured 7-Domain Knowledge Engine (`src/hijaiyyah/nui/knowledge.py::query`)
        kb_queries: list[str] = []

        first_word, _, rest_subject = q_clean.partition(" ")
        if first_word.lower() in nui_knowledge.KINDS and rest_subject.strip():
            kb_queries.append(f"{first_word.lower()} {rest_subject.strip()}")

        if has_word_boundary_match("opcode", q_norm) or has_word_boundary_match("instruksi", q_lower):
            for op_name in OpCode.__members__:
                if has_word_boundary_match(op_name, q_clean):
                    kb_queries.append(f"opcode {op_name}")
                    break
        else:
            for op_name in (
                "HLOAD", "HCADD", "HNRM2", "HDIST", "HDOT", "HGRD",
                "CGET", "CSET", "CMOV", "CZERO", "CEQ", "CRHO", "CU", "CMOD4",
                "HPACK", "HCRC", "EMITS", "FRD", "FWR", "ERET", "SYSCALL",
            ):
                if has_word_boundary_match(op_name, q_clean):
                    kb_queries.append(f"opcode {op_name}")
                    break

        try:
            known_hasm = program_index.programs().hasm
            for prog_path in known_hasm:
                base_name = prog_path.rsplit("/", 1)[-1]
                stem_name = base_name.rsplit(".", 1)[0]
                if base_name.lower() in q_lower or (
                    len(stem_name) >= 5 and has_word_boundary_match(stem_name, q_lower)
                ):
                    kb_queries.append(f"program {base_name}")
                    break
        except Exception:
            pass

        if "off-print-silicon" in q_lower:
            kb_queries.append("off OFF-PRINT-SILICON")

        if has_word_boundary_match("huruf", q_lower) or any(
            e.char in q_clean for e in MASTER_TABLE.all_entries()
        ):
            for entry in MASTER_TABLE.all_entries():
                if entry.char in q_clean or has_word_boundary_match(entry.name.lower(), q_lower):
                    kb_queries.append(f"letter {entry.name}")
                    break

        rtl_match = re.search(r"\b(hcpu_[a-z0-9_]+|hijaiyyah_[a-z0-9_]+)\b", q_lower)
        if rtl_match:
            kb_queries.append(f"rtl {rtl_match.group(1)}")
        elif has_word_boundary_match("hcpu", q_lower):
            kb_queries.append("rtl hcpu_top")

        for term in self.CANONICAL_TERMS:
            if has_word_boundary_match(term, q_clean) or has_word_boundary_match(term, q_norm):
                kb_queries.append(f"term {term}")

        if any(
            has_word_boundary_match(w, q_norm)
            for w in ("tang nano", "gowin", "board", "bitstream", "fpga")
        ):
            kb_queries.append("hardware identity")
            kb_queries.append("board latest")

        seen_kb: set[str] = set()
        for kb_q in kb_queries:
            if kb_q in seen_kb:
                continue
            seen_kb.add(kb_q)
            try:
                ans = nui_knowledge.query(kb_q)
                domain_lines: list[str] = []
                for dom in ("NUI", "HISA", "RTL", "HC", "PAPAN", "OFF", "HOST"):
                    items = ans.get(dom) or []
                    for item in items[:3]:
                        domain_lines.append(
                            f"- [{dom}] {json.dumps(item, ensure_ascii=False)[:260]}"
                        )
                if domain_lines:
                    cited_sources = nui_knowledge.sources(ans)
                    primary_src = cited_sources[0] if cited_sources else "src/hijaiyyah/nui/knowledge.py"
                    structured_sources.append(
                        RetrievedContextSource(
                            file_path=primary_src,
                            title=f"NUI Knowledge L9 (`{kb_q}`)",
                            section=f"knowledge.query('{kb_q}')",
                            relevance_score=10.5,
                            git_commit=commit_id,
                            epistemic_class="KNOWLEDGE_L9_7DOMAIN",
                            excerpt="\n".join(domain_lines[:6]),
                        )
                    )
            except Exception:
                continue

        return structured_sources

    def retrieve(
        self,
        query_text: str,
        *,
        custom_knowledge_items: list[dict[str, Any]] | None = None,
        max_sources: int = 5,
    ) -> list[RetrievedContextSource]:
        q_clean = query_text.strip()
        q_lower = q_clean.lower()
        q_norm = normalize_indonesian_query(q_lower)

        # Gate 1: Check intent classification and CosmicTera domain relevance first.
        # General AI questions (coding, Python, REST vs GraphQL, web dev, debugging), greetings,
        # capability inquiries, and system diagnostics MUST NEVER pull repository facts.
        mode_info = classify_response_mode(q_clean)
        if mode_info["mode"] in {
            "CONVERSATIONAL",
            "CAPABILITY_INQUIRY",
            "GENERAL_INTELLIGENCE",
            "SYSTEM_DIAGNOSTICS",
        }:
            return []

        if not is_cosmictera_domain_query(q_clean):
            return []

        if q_lower in {
            "contohnya",
            "contohnya?",
            "maksudnya",
            "maksudnya?",
            "lanjutkan",
            "lanjutkan.",
        }:
            return []

        raw_words = re.findall(r"[a-zA-Z0-9_\-\u0600-\u06FF]{2,}", q_norm)
        tokens: list[str] = []
        for w in raw_words:
            if w in self.STOPWORDS:
                continue
            norm_w = normalize_indonesian_token(w)
            if norm_w in self.STOPWORDS or len(norm_w) < 2:
                continue
            if norm_w not in tokens:
                tokens.append(norm_w)
            if w != norm_w and w not in tokens:
                tokens.append(w)

        commit_id = self.persona_loader.get_git_head_short()
        results: list[RetrievedContextSource] = []

        # 0. Query structured NUI Knowledge (`knowledge.py::query` & `usr.py::parse_phrase`) first
        results.extend(self.retrieve_structured_knowledge(q_clean, commit_id))

        # 0B. If asking about the function/purpose of the CosmicTera repository, include repository overview
        if mode_info["mode"] == "REPOSITORY_AUDIT" and mode_info.get("sub_intent") == "repository_purpose":
            results.append(
                RetrievedContextSource(
                    file_path="NUI/LAYERS.md",
                    title="Fungsi & Arsitektur Repository CosmicTera (Matematika Hijaiyyah — From Letter to Silicon)",
                    section="Ikhtisar Ekosistem CosmicTera",
                    relevance_score=11.5,
                    git_commit=commit_id,
                    epistemic_class="DOCUMENTATION",
                    excerpt=(
                        "Repository CosmicTera (`/Users/AMRA/hijaiyyah-mathematics`) adalah ekosistem komputasi terverifikasi "
                        "berbasis Matematika Hijaiyyah dari huruf hingga silikon:\n"
                        "1. `src/hijaiyyah/core/`: Master Table 28 huruf Hijaiyyah × vektor Hybit 18D dan invarian Six-Guard (G1–G4, T1–T2).\n"
                        "2. `src/hijaiyyah/hisa/` & `src/hijaiyyah/nui/usr.py`: Rantai kompilasi Hybit Code (HC) -> H-ISA Assembly (.hasm) -> Bytecode (.hbc) & simulator bit-exact HISAMachine.\n"
                        "3. `rtl/`: Prosesor 5-tahap HCPU (`hcpu_top.v`, 84 opcode RTL, 74 opcode P3), kriptografi Ka'bah Sponge 1600-bit, Jamrah 7-node, USSS Security, dan tampilan HDMI 1280×720@60Hz (`hcpu_hdmi_top.v`, 86.01 MHz) pada FPGA Sipeed Tang Nano 20K.\n"
                        "4. `src/hijaiyyah/nui/` & `nui-desktop/`: Arsitektur kecerdasan NUI L0–L11 (27 fakta tersegel L0, graf pengetahuan 7-domain L9) dan lingkungan kerja cerdas CosmicTera NUI Desktop."
                    ),
                )
            )

        if not tokens and not results:
            return []

        # 1. Check custom learned knowledge items (Self-Learning reuse) using strict word boundaries
        if custom_knowledge_items and tokens:
            for item in custom_knowledge_items:
                title = str(item.get("title", ""))
                content = str(item.get("content", ""))
                hay = f"{title} {content}"
                matched_toks = [tok for tok in tokens if has_word_boundary_match(tok, hay)]
                if matched_toks:
                    score = sum(3.0 for _ in matched_toks)
                    if len(matched_toks) >= 2:
                        score += 2.5
                    if score >= 3.0:
                        results.append(
                            RetrievedContextSource(
                                file_path=str(
                                    item.get("source_path")
                                    or f"self_learning:{item.get('item_id', 'kb')}"
                                ),
                                title=title,
                                section=f"Self-Learning ({item.get('provenance', 'Verified')})",
                                relevance_score=round(score + 2.0, 2),
                                git_commit=commit_id,
                                epistemic_class=str(item.get("provenance", "VERIFIED_KNOWLEDGE")),
                                excerpt=content[:900],
                            )
                        )

        # 2. Check sealed facts in `facts/` (`hijaiyyah.nui.facts`) ONLY when domain-specific triggers and high-precision tokens match
        scored_facts: list[tuple[float, Any]] = []
        for f_obj in nui_facts.load():
            fact_prefix = f_obj.fact_id.split(".", 1)[0].lower()
            domain_triggers = (
                self.FACT_DOMAIN_KEYWORDS.get(f_obj.domain.lower(), ())
                + self.FACT_DOMAIN_KEYWORDS.get(fact_prefix, ())
            )
            has_domain_trigger = any(
                has_word_boundary_match(dt, q_norm) or has_word_boundary_match(dt, q_lower)
                for dt in domain_triggers
            )
            if not has_domain_trigger:
                continue

            id_segments = [
                seg
                for seg in re.split(r"[\._]", f_obj.fact_id.lower())
                if len(seg) >= 3 and seg not in {"tier1", "exists", "the", "for", "and", "not"}
            ]
            id_hits = sum(
                4.5
                for seg in id_segments
                if has_word_boundary_match(seg, q_norm) or has_word_boundary_match(seg, q_lower)
            )
            stmt_hits = sum(
                2.5
                for tok in tokens
                if len(tok) >= 4 and has_word_boundary_match(tok, f_obj.statement)
            )
            total_fact_score = id_hits + stmt_hits + (2.0 if has_domain_trigger else 0.0)
            if total_fact_score >= 6.0:
                scored_facts.append((total_fact_score, f_obj))

        if scored_facts:
            scored_facts.sort(key=lambda x: (-x[0], x[1].fact_id))
            top_facts = [
                f"- [{f_obj.fact_id}] ({f_obj.status}): {f_obj.statement}"
                for _, f_obj in scored_facts[:4]
            ]
            results.append(
                RetrievedContextSource(
                    file_path="facts/ (src/hijaiyyah/nui/facts.py)",
                    title="Inventaris Fakta Tersegel Lapis 0",
                    section="L0 Verified Facts",
                    relevance_score=round(min(9.8, scored_facts[0][0]), 2),
                    git_commit=commit_id,
                    epistemic_class="REPOSITORY_FACT",
                    excerpt="\n".join(top_facts),
                )
            )

        # 3. Check L6 Hardware Intelligence when specifically asked with word boundary
        if (
            has_word_boundary_match("l6", q_lower)
            or has_word_boundary_match("lapis 6", q_lower)
            or has_word_boundary_match("layer 6", q_lower)
        ):
            l6_excerpt = self._extract_relevant_excerpt(
                "NUI/LAYERS.md",
                anchor="## Lapis 6 — Pemahaman perangkat keras",
                max_chars=1400,
            )
            results.append(
                RetrievedContextSource(
                    file_path="NUI/LAYERS.md",
                    title="Lapis 6 — Pemahaman Perangkat Keras & Fungsi RTL",
                    section="Lapis 6 (6.1–6.5 & Model RTL sebagai Fungsi)",
                    relevance_score=10.0,
                    git_commit=commit_id,
                    epistemic_class="DOCUMENTATION",
                    excerpt=(
                        f"{l6_excerpt}\n"
                        "Modul Python Lapis 6 di `src/hijaiyyah/nui/`: `hardware.py` (6.1), "
                        "`telemetry_sources.py` (6.2), `hardware_provenance.py` (6.3), "
                        "`hardware_state.py` (6.4), `hardware_correlation.py` (6.5), "
                        "`rtl_function.py`, `layer6_freeze.py`, dan `layer6_addendum.py`."
                    ),
                )
            )

        # 4. Score indexed repository documents & source files (including space-collapsed tokens like portal8888)
        collapsed_terms = extract_workspace_search_terms(q_clean)
        for rel_path, doc_title, kw_list in self.INDEXED_DOCUMENTS:
            p = self.repo_root / rel_path
            if not p.is_file():
                continue
            kw_hits = sum(
                2.5
                for kw in kw_list
                if has_word_boundary_match(kw, q_norm)
                or has_word_boundary_match(kw, q_lower)
                or kw in collapsed_terms
            )
            tok_hits = sum(
                1.5
                for tok in collapsed_terms
                if has_word_boundary_match(tok, rel_path)
                or has_word_boundary_match(tok, doc_title)
                or (len(tok) >= 4 and tok in rel_path.lower())
            )
            total_score = kw_hits + tok_hits
            if total_score >= 2.5:
                excerpt = self._search_lines_in_file(rel_path, collapsed_terms, max_chars=1200)
                results.append(
                    RetrievedContextSource(
                        file_path=rel_path,
                        title=doc_title,
                        section="Matched Excerpt",
                        relevance_score=round(total_score, 2),
                        epistemic_class="SOURCE_CODE" if (rel_path.startswith("src/") or rel_path.endswith(".v") or rel_path.endswith(".py")) else "DOCUMENTATION",
                        git_commit=commit_id,
                        excerpt=excerpt,
                    )
                )

        # 5. Live Workspace & Connected Folders Dynamic Discovery (catches any folder/file on disk)
        ws_scan = scan_workspace_for_query(q_clean, repo_root=self.repo_root)
        if ws_scan["summary_markdown"]:
            primary_dir = (
                ws_scan["matched_dirs"][0]
                if ws_scan["matched_dirs"]
                else (ws_scan["matched_files"][0] if ws_scan["matched_files"] else str(self.repo_root))
            )
            try:
                rel_primary = str(Path(primary_dir).relative_to(self.repo_root))
            except Exception:
                rel_primary = str(primary_dir)
            results.append(
                RetrievedContextSource(
                    file_path=rel_primary,
                    title=f"Hasil Pemindaian Langsung Folder & Berkas Repo (`{rel_primary}`)",
                    section="Live Workspace & Connected Folder Discovery",
                    relevance_score=12.5,
                    git_commit=commit_id,
                    epistemic_class="SOURCE_CODE",
                    excerpt=ws_scan["summary_markdown"][:2400],
                )
            )

        dedup: dict[str, RetrievedContextSource] = {}
        for item in sorted(results, key=lambda x: x.relevance_score, reverse=True):
            if item.file_path not in dedup:
                dedup[item.file_path] = item
            if len(dedup) >= max_sources:
                break
        return list(dedup.values())

    def retrieve_context(
        self,
        query_text: str,
        *,
        top_k: int = 5,
        learned_items: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Return structured retrieval bundle with metadata and scores."""
        mode_info = classify_response_mode(query_text)
        sources = self.retrieve(
            query_text,
            custom_knowledge_items=learned_items,
            max_sources=top_k,
        )
        items = [
            {
                "file_path": s.file_path,
                "title": s.title,
                "section": s.section,
                "relevance_score": s.relevance_score,
                "git_commit": s.git_commit,
                "epistemic_class": s.epistemic_class,
                "excerpt": s.excerpt,
            }
            for s in sources
        ]
        return {
            "query": query_text,
            "intent_mode": mode_info["mode"],
            "sub_intent": mode_info.get("sub_intent"),
            "is_cosmictera_specific": mode_info.get("is_cosmictera_specific", False),
            "items": items,
            "total_matches": len(items),
        }

    def _extract_relevant_excerpt(
        self, rel_path: str, anchor: str, max_chars: int = 1200
    ) -> str:
        p = self.repo_root / rel_path
        if not p.is_file():
            return ""
        text = p.read_text(encoding="utf-8", errors="replace")
        idx = text.find(anchor)
        if idx >= 0:
            return text[idx : idx + max_chars].strip()
        return text[:max_chars].strip()

    def _search_lines_in_file(
        self, rel_path: str, tokens: list[str], max_chars: int = 900
    ) -> str:
        p = self.repo_root / rel_path
        if not p.is_file():
            return ""
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        matched_windows: list[str] = []
        for idx, line in enumerate(lines):
            if any(has_word_boundary_match(tok, line) for tok in tokens):
                start = max(0, idx - 1)
                end = min(len(lines), idx + 4)
                snippet = "\n".join(f"L{ln+1}: {lines[ln]}" for ln in range(start, end))
                matched_windows.append(snippet)
                if sum(len(w) for w in matched_windows) >= max_chars:
                    break
        if matched_windows:
            return "\n...\n".join(matched_windows)[:max_chars]
        return "\n".join(lines[:20])[:max_chars]

    @staticmethod
    def build_windowed_conversation_history(
        messages: list[dict[str, Any]],
        *,
        max_recent_messages: int = 12,
        max_total_chars: int = 14000,
    ) -> tuple[list[dict[str, str]], str | None]:
        """Manage conversation context window: keep recent turns verbatim and summarize older turns."""
        if not messages:
            return ([], None)

        clean_msgs: list[dict[str, str]] = []
        for m in messages:
            role = str(m.get("role", "user"))
            if role not in {"user", "assistant", "system", "tool"}:
                role = "user"
            content = str(m.get("content", "")).strip()
            if content:
                clean_msgs.append({"role": role, "content": content})

        if len(clean_msgs) <= max_recent_messages:
            return (clean_msgs, None)

        older = clean_msgs[:-max_recent_messages]
        recent = clean_msgs[-max_recent_messages:]

        user_questions = [m["content"] for m in older if m["role"] == "user"]
        summary_lines = [
            f"- Total pesan terdahulu yang diringkas: {len(older)} pesan.",
        ]
        if user_questions:
            summary_lines.append(f"- Pertanyaan pertama pengguna di sesi ini: \"{user_questions[0][:200]}\"")
            if len(user_questions) > 1:
                summary_lines.append(
                    "- Topik terdahulu lainnya: "
                    + "; ".join(f"\"{q[:80]}\"" for q in user_questions[1:5])
                )

        budgeted_recent: list[dict[str, str]] = []
        used = 0
        for m in reversed(recent):
            c_len = len(m["content"])
            if used + c_len > max_total_chars and budgeted_recent:
                break
            budgeted_recent.append(m)
            used += c_len
        budgeted_recent.reverse()

        return (budgeted_recent, "\n".join(summary_lines))
