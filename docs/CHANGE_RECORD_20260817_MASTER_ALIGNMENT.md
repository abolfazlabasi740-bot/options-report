# Change Record — 2026-08-17

- What: هم‌ترازسازی پروژه با Master Project Book جدید.
- Why: رفع معرفی اشتباه V4، اصلاح وزن Market Structure، تکمیل Version/Audit/Feature Registry و ثبت Known Gapهای واقعی.
- Evidence: `master project book/Master Project Book.docx` با SHA-256 ثبت‌شده در Config.
- Affected: Config، Financial، Analytics، Scoring، Risk، Decision، Reporting، Audit، Learning، Knowledge، Pipeline، Tests و مستندات.
- Expected impact: رتبه‌بندی Market Structure فقط از عوامل مصوب استفاده می‌کند؛ خروجی‌ها نسخه و Lineage کامل‌تری دارند؛ V4 به‌عنوان Candidate باقی می‌ماند.
- Recovery: نسخه‌ها و گزارش‌های تاریخی حذف نمی‌شوند. Artifactهای قبلی با Version قبلی قابل بازیابی می‌مانند.
- Validation: Master governance PASS؛ PowerShell parse PASS؛ Python compile PASS؛ Smoke Test PASS؛ Deterministic replay PASS؛ Artifact hash verification PASS.
- Status: COMPLETED_WITH_KNOWN_GAPS
