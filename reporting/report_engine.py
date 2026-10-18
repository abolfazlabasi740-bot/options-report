#!/usr/bin/env python3
"""
report_engine.py — موتور مشترک گزارش‌دهی OptimusAI V41
بر اساس Master_Project_Book_v3.docx بخش ۱۵
هر گزارش جدید فقط name + columns + build_rows تعریف می‌کند؛
بقیه (Run ID, Timestamp, Lineage, Validation, JSON/Excel/MD/Bale) خودکار است.
"""
import json, hashlib, os
from datetime import datetime, timezone, timedelta
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

# ── ثابت‌های مشترک ──────────────────────────────────────────
IRST = timezone(timedelta(hours=3, minutes=30))
EXCEL_FONT = "B Nazanin"
FONT_SIZE = 11
MAX_COLS = 11


def now_ir() -> str:
    """timestamp فارسی، ISO با منطقه زمانی ایران"""
    return datetime.now(IRST).strftime("%Y-%m-%d %H:%M:%S%z")


def gen_run_id(seed: str = "") -> str:
    """شناسه یکتای اجرا — sha256 خلاصه‌شده"""
    raw = f"{seed}:{datetime.now(IRST).isoformat()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ── پاکت گزارش (Envelope) ──────────────────────────────────
class ReportEnvelope:
    """پاکت مشترک همه گزارش‌ها — تطبیق با V3 بخش ۱۵"""
    def __init__(self, report_name: str, scenario: str = "",
                 price_basis: str = "", market_open: bool = False,
                 input_snapshot: Dict = None, fixed_growth: Any = None):
        self.run_id          = gen_run_id(report_name)
        self.timestamp       = now_ir()
        self.report_name     = report_name
        self.scenario        = scenario
        self.price_basis     = price_basis
        self.market_open     = market_open
        self.fixed_growth    = fixed_growth
        self.input_snapshot  = input_snapshot or {}
        self.missing_data    = []
        self.flags           = []
        self.validation_pass = False
        self.confidence      = None
        self.score_summary   = {}
        self.ranking_top     = []

    def add_missing(self, item: str):
        if item and item not in self.missing_data:
            self.missing_data.append(item)

    def add_flag(self, flag: str):
        if flag and flag not in self.flags:
            self.flags.append(flag)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id":          self.run_id,
            "timestamp":       self.timestamp,
            "report_name":     self.report_name,
            "scenario":        self.scenario,
            "price_basis":     self.price_basis,
            "market_open":     self.market_open,
            "fixed_growth":    self.fixed_growth,
            "input_snapshot":  self.input_snapshot,
            "missing_data":    self.missing_data,
            "flags":           self.flags,
            "validation_pass": self.validation_pass,
            "confidence":      self.confidence,
            "score_summary":   self.score_summary,
            "ranking_top":     self.ranking_top,
        }


# ── چک‌لیست اعتبارسنجی V3 ──────────────────────────────────
def validate_checklist(envelope: ReportEnvelope, rows: List[Dict],
                       required_fields: List[str]) -> bool:
    """
    چک‌لیست اجباری صدور گزارش — V3 بخش ۱۵
    اگر هر مورد ناقص باشد، validation_pass = False و دلیل در missing_data ثبت می‌شود.
    """
    ok = True
    if not rows:
        envelope.add_missing("هیچ ردیف داده‌ای برای گزارش وجود ندارد")
        ok = False
    for field in required_fields:
        missing_count = sum(1 for r in rows if r.get(field) is None)
        if missing_count > 0:
            envelope.add_missing(f"فیلد '{field}' در {missing_count} ردیف خالی است")
            ok = False
    if not envelope.scenario:
        envelope.add_missing("سناریو مشخص نشده")
        ok = False
    if not envelope.price_basis:
        envelope.add_missing("مبنای قیمت مشخص نشده")
        ok = False
    envelope.validation_pass = ok
    return ok


# ── کلاس پایه گزارش ────────────────────────────────────────
class BaseReport(ABC):
    """
    کلاس پایه — هر گزارش این را ارث می‌برد.
    فقط name, columns, build_rows را پیاده‌سازی کنید.
    """
    name:        str              = ""
    slug:        str              = ""
    columns:     List[str]        = []
    required:    List[str]        = []
    output_dir:  str              = "output/reports"

    @abstractmethod
    def build_rows(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """داده خام را به لیست دیکشنری با کلیدهای columns تبدیل کند"""
        ...

    def envelope_kwargs(self) -> Dict:
        """فرزندها می‌توانند فیلدهای envelope را تنظیم کنند"""
        return {}

    # ── خروجی JSON ──────────────────────────────────────────
    def to_json(self, rows: List[Dict], unmatched: List[Dict] = None,
                no_ceiling: List[Dict] = None, extra: Dict = None) -> Dict:
        env = ReportEnvelope(self.name, **self.envelope_kwargs())
        validate_checklist(env, rows, self.required)

        # محاسبات خلاصه‌ای
        total = len(rows) + len(unmatched or []) + len(no_ceiling or [])
        env.score_summary = {
            "total_items":   total,
            "matched":       len(rows),
            "unmatched":     len(unmatched or []),
            "no_ceiling":    len(no_ceiling or []),
        }
        if rows:
            sorted_rows = sorted(
                rows,
                key=lambda r: r.get("score", r.get("امتیاز", 0)),
                reverse=True
            )
            env.ranking_top = [
                {k: v for k, v in r.items() if k in ("symbol", "نماد", "score", "امتیاز", "status", "وضعیت")}
                for r in sorted_rows[:10]
            ]

        data = {
            **env.to_dict(),
            "methodology":  "LMP Scanner V41 — Deterministic Pipeline",
            "total_calls":  total,
            "opportunities": len(rows),
            "unmatched":    unmatched or [],
            "no_ceiling":   no_ceiling or [],
            "results":      rows,
        }
        if extra:
            data.update(extra)
        return data

    # ── خروجی Excel ─────────────────────────────────────────
    def to_excel(self, rows: List[Dict], filepath: str,
                 basis_fa: str = "", fixed_growth: Any = None):
        import openpyxl
        from openpyxl.styles import Font, Alignment
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = self.name[:31]
        ws.sheet_view.rightToLeft = True

        cols = self.columns[:MAX_COLS]
        hfont = Font(name=EXCEL_FONT, size=FONT_SIZE, bold=True)
        bfont = Font(name=EXCEL_FONT, size=FONT_SIZE)
        calign = Alignment(horizontal="center", vertical="center", wrap_text=True)

        # هدر
        for i, col in enumerate(cols, 1):
            c = ws.cell(row=1, column=i, value=col)
            c.font = hfont
            c.alignment = calign
            ws.column_dimensions[get_column_letter(i)].width = 16

        # ردیف‌ها
        for ridx, row in enumerate(rows, 2):
            for cidx, col in enumerate(cols, 1):
                val = row.get(col, row.get(self._en_key(col), ""))
                c = ws.cell(row=ridx, column=cidx, value=val)
                c.font = bfont
                c.alignment = calign

        # ردیف سربه‌سر / جمع
        if rows:
            total_row = ridx + 1
            ws.cell(row=total_row, column=1, value="جمع").font = hfont
            ws.cell(row=total_row, column=1).alignment = calign

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        wb.save(filepath)
        return filepath

    @staticmethod
    def _en_key(fa_col: str) -> str:
        """نگاشت کلید فارسی به انگلیسی برای جستجوی داده"""
        mapping = {
            "نماد": "symbol", "نوع": "type", "قیمت پایه": "base_price",
            "قیمت اعمال": "strike", "سقف قیمت": "ceiling",
            "پرمیوم": "premium", "سود خام": "raw_profit",
            "سربه‌سر": "break_even", "امتیاز": "score", "وضعیت": "status",
            "ردیف": "row",
        }
        return mapping.get(fa_col, fa_col)

    # ── خروجی Markdown ──────────────────────────────────────
    def to_markdown(self, json_data: Dict) -> str:
        env = json_data
        lines = [
            f"# گزارش: {env.get('report_name', self.name)}",
            f"",
            f"| فیلد | مقدار |",
            f"|---|---|",
            f"| Run ID | `{env.get('run_id', '')}` |",
            f"| زمان | {env.get('timestamp', '')} |",
            f"| سناریو | {env.get('scenario', '')} |",
            f"| مبنای قیمت | {env.get('price_basis', '')} |",
            f"| بازار | {'باز' if env.get('market_open') else 'بسته'} |",
            f"| اعتبارسنجی | {'✅ مجاز' if env.get('validation_pass') else '❌ ناقص'} |",
            f"| کل آیتم‌ها | {env.get('total_calls', 0)} |",
            f"| فرصت‌ها | {env.get('opportunities', 0)} |",
            f"",
        ]
        if env.get("missing_data"):
            lines.append("## داده‌های مفقودی")
            for m in env["missing_data"]:
                lines.append(f"- {m}")
            lines.append("")
        if env.get("flags"):
            lines.append("## هشدارها")
            for f in env["flags"]:
                lines.append(f"- {f}")
            lines.append("")
        if env.get("results"):
            lines.append("## نتایج")
            lines.append("| " + " | ".join(self.columns[:MAX_COLS]) + " |")
            lines.append("|" + "---|" * len(self.columns[:MAX_COLS]))
            for r in env["results"][:20]:
                vals = [str(r.get(c, r.get(self._en_key(c), ""))) for c in self.columns[:MAX_COLS]]
                lines.append("| " + " | ".join(vals) + " |")
            lines.append("")
        if env.get("ranking_top"):
            lines.append("## رتبه‌بندی Top-10")
            for i, r in enumerate(env["ranking_top"], 1):
                lines.append(f"{i}. {r}")
            lines.append("")
        lines.append("---")
        lines.append(f"*تولید‌شده توسط OptimusAI V41 Report Engine*")
        return "\n".join(lines)

    # ── اجرای کامل ─────────────────────────────────────────
    def run(self, *args, **kwargs) -> Dict:
        """اجرای کامل: داده → JSON → Excel → Markdown → مسیر خروجی"""
        rows, unmatched, no_ceiling, extra = self.build_rows(*args, **kwargs)

        json_data = self.to_json(rows, unmatched, no_ceiling, extra)

        slug = self.slug or self.name.replace(" ", "_").lower()
        base = os.path.join(self.output_dir, slug)
        os.makedirs(base, exist_ok=True)

        json_path   = os.path.join(base, "latest.json")
        excel_path  = os.path.join(base, "latest.xlsx")
        md_path     = os.path.join(base, "latest.md")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        self.to_excel(rows, excel_path,
                      basis_fa=json_data.get("price_basis", ""),
                      fixed_growth=json_data.get("fixed_growth"))

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self.to_markdown(json_data))

        json_data["_paths"] = {"json": json_path, "excel": excel_path, "md": md_path}
        return json_data


# ── ثبت‌نام گزارش‌ها ───────────────────────────────────────
_REPORT_REGISTRY: Dict[str, type] = {}

def register(cls):
    """دیکوریتور ثبت گزارش در رجیستری"""
    _REPORT_REGISTRY[cls.name] = cls
    return cls

def get_report(name: str) -> Optional[type]:
    return _REPORT_REGISTRY.get(name)

def list_reports() -> List[str]:
    return list(_REPORT_REGISTRY.keys())
