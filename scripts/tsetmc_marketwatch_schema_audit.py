import json
import hashlib
from pathlib import Path
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

base = Path("output/history/tsetmc_api_archive/universe")
source = base / "market_watch_cdn.response"
out = base / "marketwatch_schema_audit.json"

if not source.exists():
    raise SystemExit(f"ERROR: raw source not found: {source}")

raw = source.read_bytes()
data = json.loads(raw.decode("utf-8-sig"))

if not isinstance(data, dict) or not isinstance(data.get("marketwatch"), list):
    raise SystemExit("ERROR: unexpected Market Watch structure; raw file preserved")

rows = data["marketwatch"]
key_counts = Counter()
value_samples = {}
type_counts = Counter()
candidate_ids = (
    "insCode", "instrumentCode", "instrumentId",
    "instrumentID", "id", "nscCode"
)
candidate_names = (
    "lVal18AFC", "lVal30", "instrumentName",
    "name", "symbol", "symbolName"
)
candidate_types = (
    "cEtaval", "market", "marketCode", "instrumentType",
    "flow", "cgrValCot"
)

for row in rows:
    if not isinstance(row, dict):
        type_counts[type(row).__name__] += 1
        continue
    type_counts["object"] += 1
    for key, value in row.items():
        key_counts[key] += 1
        if key not in value_samples and value is not None:
            value_samples[key] = {
                "type": type(value).__name__,
                "sample": str(value)[:180]
            }

def summarize_candidates(fields):
    result = {}
    for field in fields:
        present = [r.get(field) for r in rows
                   if isinstance(r, dict) and r.get(field) not in (None, "")]
        distinct = len({str(v) for v in present})
        result[field] = {
            "present": len(present),
            "distinct": distinct,
            "examples": [str(v)[:100] for v in present[:5]]
        }
    return result

audit = {
    "created_at": datetime.now(ZoneInfo("Asia/Tehran")).isoformat(),
    "source": str(source),
    "source_sha256": hashlib.sha256(raw).hexdigest(),
    "source_bytes": len(raw),
    "root_keys": list(data.keys()),
    "record_count": len(rows),
    "row_types": dict(type_counts),
    "field_presence_counts": dict(key_counts),
    "field_samples": value_samples,
    "candidate_id_fields": summarize_candidates(candidate_ids),
    "candidate_name_fields": summarize_candidates(candidate_names),
    "candidate_type_fields": summarize_candidates(candidate_types),
    "sample_records": [
        r for r in rows[:3] if isinstance(r, dict)
    ],
    "production_signal": "OFF",
    "trading_signal_generation": "FORBIDDEN"
}

out.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

print("========== TSETMC MARKETWATCH SCHEMA AUDIT ==========")
print("SOURCE:", source)
print("SOURCE_SHA256:", audit["source_sha256"])
print("RECORDS:", len(rows))
print("ROW_TYPES:", json.dumps(audit["row_types"], ensure_ascii=False))
print("FIELDS:", json.dumps(audit["field_presence_counts"], ensure_ascii=False))
print("CANDIDATE_IDS:", json.dumps(audit["candidate_id_fields"], ensure_ascii=False))
print("CANDIDATE_NAMES:", json.dumps(audit["candidate_name_fields"], ensure_ascii=False))
print("CANDIDATE_TYPES:", json.dumps(audit["candidate_type_fields"], ensure_ascii=False))
print("SAMPLE_RECORDS:", json.dumps(audit["sample_records"], ensure_ascii=False))
print("AUDIT_FILE:", out)
print("PRODUCTION_SIGNAL: OFF")
print("TRADING_SIGNAL_GENERATION: FORBIDDEN")
