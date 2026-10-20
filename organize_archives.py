import os, re, json, shutil, hashlib
from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()
OUT = ROOT / "output"
ARCHIVE = OUT / "central_archive"
MANIFEST = ARCHIVE / "archive_manifest.json"

LATEST = [
    ("output/base_share/latest_whole_market_opportunity_report.json", "base_share"),
    ("output/base_share/latest_whole_market_opportunity_report.txt", "base_share"),
    ("output/base_share/latest_plain_symbol_trend_report.json", "base_share"),
    ("output/latest_report.txt", "reports"),
    ("output/tsetmc_first/latest_report.txt", "tsetmc"),
]

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def date_from_path(path):
    s = str(path)
    m = re.search(r"(?<!\d)(20\d{2})[-_]?(\d{2})[-_]?(\d{2})(?!\d)", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None

def record_date(src):
    d = date_from_path(src)
    if d:
        return d
    if src.suffix.lower() == ".json":
        try:
            obj = json.loads(src.read_text(encoding="utf-8"))
            if isinstance(obj, dict):
                for k in ("latest_market_date", "market_date", "snapshot_date", "date"):
                    v = obj.get(k)
                    if v:
                        v = str(v)[:10]
                        m = re.search(r"(20\d{2})[-/]?(\d{2})[-/]?(\d{2})", v)
                        if m:
                            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                for k in ("latest_market_date_jalali", "market_date_jalali"):
                    v = obj.get(k)
                    if v:
                        return "jalali-" + re.sub(r"[^0-9]", "-", str(v)).strip("-")
        except Exception:
            pass
    try:
        return datetime.fromtimestamp(src.stat().st_mtime).strftime("%Y-%m-%d")
    except Exception:
        return "undated"

def category(src):
    s = str(src).replace("\\", "/").lower()
    if "/daily_history/" in s:
        return "base_share/daily_history"
    if "/github_evidence/" in s:
        return "evidence"
    if "/tsetmc_first/" in s or "tsetmc" in src.name.lower() or "snapshot" in src.name.lower():
        return "tsetmc"
    if "/base_share/" in s:
        return "base_share"
    return "reports"

def sources():
    found = set()
    for rel, _ in LATEST:
        p = ROOT / rel
        if p.is_file():
            found.add(p.resolve())

    daily = OUT / "base_share" / "daily_history"
    if daily.is_dir():
        for p in daily.rglob("*"):
            if p.is_file():
                found.add(p.resolve())

    evidence = OUT / "github_evidence"
    if evidence.is_dir():
        for p in evidence.rglob("*"):
            if p.is_file():
                found.add(p.resolve())

    # گزارش‌های متنی و داده‌های اسنپ‌شات/گزارش در مسیرهای شناخته‌شده
    for folder in (OUT / "tsetmc_first", OUT / "base_share", OUT):
        if not folder.is_dir():
            continue
        for p in folder.iterdir():
            if not p.is_file():
                continue
            n = p.name.lower()
            if any(x in n for x in ("snapshot", "latest_report", "latest_whole_market", "latest_plain_symbol")):
                found.add(p.resolve())

    return sorted(p for p in found if ARCHIVE.resolve() not in p.parents)

ARCHIVE.mkdir(parents=True, exist_ok=True)
try:
    old = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
except Exception:
    old = {}
entries = old.get("files", [])
known = {e.get("source") for e in entries}
added = 0
errors = []

for src in sources():
    try:
        rel = src.relative_to(ROOT).as_posix()
        day = record_date(src)
        cat = category(src)
        dest_dir = ARCHIVE / day / cat
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name

        # در صورت برخورد نام، نام یکتا بر اساس مسیر مبدأ ساخته می‌شود.
        if dest.exists() and sha256(dest) != sha256(src):
            tag = hashlib.sha256(rel.encode()).hexdigest()[:10]
            dest = dest_dir / f"{src.stem}__{tag}{src.suffix}"

        digest = sha256(src)
        if not dest.exists():
            shutil.copy2(src, dest)

        if rel not in known:
            entries.append({
                "source": rel,
                "archive_copy": dest.relative_to(ROOT).as_posix(),
                "date_bucket": day,
                "category": cat,
                "size_bytes": src.stat().st_size,
                "sha256": digest,
                "copied_at": datetime.now().isoformat(timespec="seconds"),
                "verification": "MATCH" if sha256(dest) == digest else "MISMATCH"
            })
            known.add(rel)
            added += 1
    except Exception as e:
        errors.append(f"{src}: {e}")

manifest = {
    "schema_version": "1.0",
    "created_at": datetime.now().isoformat(timespec="seconds"),
    "policy": "COPY_ONLY_NO_SOURCE_DELETION",
    "archive_root": ARCHIVE.relative_to(ROOT).as_posix(),
    "files": entries,
    "errors": errors
}
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

verified = sum(e.get("verification") == "MATCH" for e in entries)
print("ARCHIVE_ORGANIZATION_FINISHED")
print("ARCHIVE_ROOT:", ARCHIVE)
print("MANIFEST:", MANIFEST)
print("NEW_ENTRIES:", added)
print("MANIFEST_ENTRIES:", len(entries))
print("HASH_VERIFIED:", verified)
print("ERRORS:", len(errors))
for e in errors[:10]:
    print("ERROR:", e)
