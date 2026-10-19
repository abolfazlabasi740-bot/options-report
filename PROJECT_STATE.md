# OptimusAI V4.1 — سند وضعیت پروژه (Source of Truth)

**تاریخ سند:** 1405/07/24 (2026-10-16)

> این سند تک‌مرجع (Single Source of Truth) وضعیت پروژه است تا از بازساختِ کارهای انجام‌شده جلوگیری شود. پیش از هر تغییر، ابتدا این فایل را بخوانید.

---

## بخش ۱ — جهان قفلشدهٔ ۲۶ سهمی (Locked Universe)

نگاشت underlying → پیشوند اختیار معامله، به همین ترتیب:

| # | Underlying | پیشوند اختیار |
|---|-----------|---------------|
| 1 | اخابر | ضمخا |
| 2 | اطلس | ضاطلس |
| 3 | اهرم | ضهرم |
| 4 | بساما | ضبساما |
| 5 | تاپیکو | ضپیک |
| 6 | توان | ضتوان |
| 7 | جوانه.ک | ضجوا |
| 8 | تاپیکو/تاصیکو | ضتاص |
| 9 | خبهمن | ضهمن |
| 10 | خساپا | ضسپا |
| 11 | خودرو | ضخود |
| 12 | دارونو | ضدرو |
| 13 | دزاگرس | ضدزاگرس |
| 14 | ذوب | ضذوب |
| 15 | شپنا | ضشنا |
| 16 | شستا | ضستا |
| 17 | طعام | ضطعام |
| 18 | فرابورس | ضفرابورس |
| 19 | فزر | ضفزر |
| 20 | فملی | ضملی |
| 21 | کاریس | ضکاریس |
| 22 | موج | ضموج |
| 23 | وبصادر | ضصاد |
| 24 | وبملت | ضملت |
| 25 | وتجارت | ضجار |
| 26 | همتراز | ضراز |

---

## بخش ۲ — اینونتوری فایلها و هشهای SHA-256 (نسخهٔ مرجع)

| فایل | SHA-256 | حجم / توضیح |
|------|---------|-------------|
| `data/__init__.py` | `3f76d4f0b9506a94216bf32c45776bdd8cc579b6ad4e3c95c7e7a5958ca3b5fa` | 154 bytes |
| `data/tsetmc.py` | `2b0eecb7cff24c415c12d41db447962eced76e4f056ca00709030958b73a9f7b` | 9,769 bytes |
| `data/underlying_map.py` | `4bbbbefe484ad9987190f1d0da4455a253ace9ac45b703a34321c2023e9169c4` | 3,562 bytes |
| `reporting/repository.py` | `56abf33c9139944cab22c11a17c791eead5a05b944dcb56fe311866f125161f7` | 7,226 bytes (178 lines) — نسخهٔ پچشده؛ خط 169: `return '\n'.join(L)` تکخطی |
| `test_repository.py` | `2dc729399b209facbb162232159e026373ab86e48149631f3f3bae602374abe6` | 5,669 bytes |
| `test_tsetmc.py` | `0102c1a6a185cc2a2a1b66d8ccb457abf664d7de7da92f7b46121df3fa8cadbc` | 6,622 bytes |
| `test_underlying_map.py` | `defa96374744911d04f199226da42bf4f946a8de4eefca86cf8231b59908c04e` | 4,528 bytes |
| `deploy_optimus_modules.sh` | — | 52,953 bytes — اسکریپت استقرار خودکفا (base64 + sha256 verification + compile + tests + ALL_GREEN) |
| `install_universe_mapping.sh` | `9a8e2611990c8ea77c1525f8f9d0798ba667098ad012c0553e614e611fae3e33` | 371 lines، 15,615 bytes، `bash -n` RC=0 |
| `patch_snippet.py` | `38f35a438f0825db76a5266e47c39c1c9c335d97b386f064bbdccbbcf3de82ea` | منسوخ/غیراستفاده |
| `Master_Project_Book_v3.docx` | `71195818d4393f6c2da0d71209d5b5b61208ed3264f13b9a2790fca4a2c57831` | — |
| `Master Project Book.docx` | `3cba9235181063f040f6df83f18e2b739395528f417d1179ec02eb2ce10f9268` | — |
| `pasted-text.txt` | `0caef6c43ef10ca342e588f1fe4bb7128e901d32edd02520105f0d4b3558400b` | — |

---

## بخش ۳ — وضعیت تستها (تأییدشده روی LIVE)

| تست فایل | نتیجه | پوشش |
|----------|-------|------|
| `test_underlying_map.py` | **79/79 assertions پاس** | نگاشت کامل ۲۶سهمی، نمادهای پسونددار (ضخود5000 → خودرو)، رد نمادهای خارج از جهان (ضفول، ضگل، ضچاد، ضبندر، ضتران، ضفام)، یکپارچگی snapshot |
| `test_tsetmc.py` | **35/35 assertions پاس** | پارس، تفکیک ض/ط، مخزن latest.json، دریافت، CLI |
| `test_repository.py` | **همه assertions پاس** | anchorهای روز هفتگی (شنبه-چهارشنبه)، ساعات بازار ۰۹:۰۰-۱۲:۳۰، پارسر زمان (ISO +03:30 / Z / naive / epoch / جلالی)، منطق تازگی، رندر گزارش LMP |

- هر سه تست با **RC=0** در محیط زندهٔ Termux در مسیر `~/OptimusAI_V41_LIVE` اجرا شدند (1405/07/24).
- هشهای audit نهایی هفت‌فایلی با نسخهٔ مرجع بایتبهبایت مطابقت داشت (**ALL_GREEN**).

---

## بخش ۴ — پوشش قابل بهرهبرداری

**حدود ۸۰٪ پروژه** تکمیل و production-ready است:

- لایهٔ داده: `data/tsetmc.py`، `data/underlying_map.py`، `data/__init__.py`
- مخزن گزارشدهی: `reporting/repository.py`
- تمام تستها

همهٔ موارد بالا مستقر روی LIVE هستند. باقیمانده: موتورهای تصمیم/ریسک/یادگیری (منتظر دادهٔ واقعی).

---

## بخش ۵ — رویهٔ استقرار در Termux (تأییدشده)

دستورات دقیق:

```bash
termux-setup-storage
find ~/storage/shared -iname 'deploy_optimus_modules.sh'
cp <مسیر پیدا شده> ~/
chmod +x ~/deploy_optimus_modules.sh
bash ~/deploy_optimus_modules.sh
```

**خروجی مورد انتظار:** 7× `DEPLOYED`، 4× `COMPILE_OK`، 3× `RC=0`، جدول SHA-256، `ALL_GREEN`.

---

## بخش ۶ — کارهای انجامشده (Do-Not-Rebuild List)

- ✅ نگاشت ۲۶سهمی `underlying_map` ساخته و تست شد.
- ✅ موتور پارس TSETMC (`mw_raw.txt` → stocks/options/others `latest.json` + run_id deterministic).
- ✅ باگ `reporting/repository.py` خط 169 پیدا و پچ شد (multiline string broken).
- ✅ اسکریپت استقرار خودکفا `deploy_optimus_modules.sh` ساخته، در محیط شبیهسازیشده ALL_GREEN شد، سپس روی LIVE واقعی اجرا و ALL_GREEN شد (1405/07/24).

---

## بخش ۷ — کارهای باقیمانده (Backlog)

1. **گزارشهای دکمه شیشهای بله** (inline_keyboard + callback_query با polling tapi.bale.ai) — طراحی پیشنهادی آماده؛ نیازمند: بازرسی `reporting/bale.py` موجود در LIVE، توکن ربات، تصمیم قالب خروجی دکمه‌ها.
   - طبق `Master_Project_Book_v3.docx` بخش ۱۵: گزارش Bale از خروجی deterministic موتور گزارشدهی تولید میشود؛ منطق جدید مستقل ممنوع.
   - طبق `Master Project Book.docx` بخش ۱۷: ابزارهای Reporting شامل Excel/Markdown/Bale.
2. اتصال `data/tsetmc.py` به منبع واقعی TSETMC در LIVE و تولید اولین `latest.json` واقعی.
3. مستندسازی در GitHub (این سند نقطهٔ شروع است).
4. موتورهای Decision/Risk/Learning پس از رسیدن دادهٔ واقعی.

---

## بخش ۸ — قواعد پروژه (غیرقابل مذاکره)

- هیچ عددی بدون دادهٔ واقعی.
- هیچ سیگنالی بدون چکلیست کامل.
- هیچ دادهٔ قدیمی بدون برچسب زمانی.
- عدم تحلیل در صورت ناقص بودن داده.
- عدم بازنویسی ماژولهای موجود LIVE بدون بازرسی اول.

## بخش ۹ — مستندسازی گیت و کشف bale_listener (۱۴۰۵/۰۷/۲۴)
- ریپوی رسمی: https://github.com/abolfazlabasi740-bot/options-report.git
- کامیت مرجع: a7d0be3 — هفت فایل هستهای ALL_GREEN (بایتبهبایت با بخش ۲ مطابق)
- کشف مهم: bale_listener.py (840 خط، sha256=3597e5869514fdb9556fde3056ad60da863dc737f0f7809857a1c54f3196e49c) زیرساخت کامل دکمههای شیشهای بله را دارد:
  - منوی اصلی ۶ دکمهای + زیرمنوها + صفحهبندی symbols_page
  - polling با getUpdates، پاسخ callback با answer_callback_query
  - callback_dataها: report_ranked_15، base_stocks، report_last_minute_option_opportunity، report_activity_15، symbols_page:N، system_status، strategy_bull_call_spread، market_shares_page:N، option_shares، trend_review، lmp_opportunities، symbol:NAME، main_menu
- ⚠️ آیتم «ساخت دکمههای شیشهای» از Backlog حذف و به Do-Not-Rebuild منتقل شد
- باقیماندهٔ این آیتم: فقط راستیآزمایی وجود هندلر برای همهٔ callback_dataها (دکمهٔ مرده)

## بخش ۱۰ — راستیآزمایی و ترمیم دکمههای شیشهای (۱۴۰۵/۰۷/۲۴)
- ممیزی کامل dispatch انجام شد. نتیجهٔ ۱۳ دکمه:
  - سالم (۷): market_shares_page، option_shares(_page)، trend_review، lmp_opportunities، main_menu، strategy_bull_call_spread
  - مرده (۶): report_ranked_15، base_stocks، report_activity_15، report_last_minute_option_opportunity، system_status، symbols_page:N، symbol:NAME
- ریشهٔ باگ ۵ دکمه: تعریف تکراری CALLBACK_COMMANDS در خط ~127 (shadowing نسخهٔ کامل خط ~77) → حذف شد
- ریشهٔ باگ نمادها: symbols_page:N و symbol:NAME هندلر callback نداشتند → دو elif با استفاده از send_symbol_menu و generate_report موجود افزوده شد
- راستیآزمایی: py_compile + تأیید AST دیکشنری نهایی؛ هش و خطوط جدید در گام بعدی ثبت شد
- آیتم دکمههای شیشهای: بسته (۱۳/۱۳) — Do-Not-Rebuild


## بخش ۱۱ — پایپ‌لاین بررسی بورس‌ویو (۱۴۰۵/۰۷/۲۸)
- سند اجرایی و دفتر شواهد ایجاد شد: [docs/BOURSEVIEW_CAPABILITY_PIPELINE.md](docs/BOURSEVIEW_CAPABILITY_PIPELINE.md)
- کامیت ایجاد سند: d613e859e2529e99d8089a127f12530982a2a975
- دامنه سند: قابلیت‌ها و فیلترهای عمومی بورس‌ویو، شواهد و URLها، نگاشت قابلیت به منبع داده، مراحل اجرایی، معیار عبور، زمان‌بندی نسبی و قواعد جلوگیری از دوباره‌کاری.
- شواهد عمومی فعلی: فیلترهای رشد درآمد ماهانه/فصلی، بهبود حاشیه سود عملیاتی، P/S ماهانه، RSI و حجم مشکوک؛ نمونه فیلتر شرکت‌های سرمایه‌گذاری زیر NAV.
- وضعیت دسترسی: مسیرهای عمومی tickers و quotes در بررسی قبلی دیده شده‌اند اما schema و کیفیت پاسخ هنوز کامل اعتبارسنجی نشده؛ API اختصاصی نیازمند مستندات/دسترسی رسمی است.
- گام بعدی ثبت‌شده: ممیزی data/tsetmc.py و تست‌های موجود از GitHub، سپس تعیین شکاف پوشش فیلدها؛ پیش از بازرسی، ماژول جدید ساخته نشود.
- فقط مستندسازی GitHub انجام شد؛ هیچ اجرای Termux و هیچ تغییر LIVE انجام نشده است.


## بخش ۱۲ — تکمیل بررسی عمومی بورس‌ویو و ارزیابی خرید API (۱۴۰۵/۰۷/۲۸)
- بررسی تکمیلی کانال رسمی، قابلیت‌های صفحه بازار/نماد/صنعت، تفکیک داخلی و صادراتی تولید و فروش، بیش از ۷۰ اندیکاتور و الگوهای تکنیکال، نقشه صندوق‌ها و اوراق، داده‌های کلان، منحنی نرخ بهره و امکانات اعلام‌شده پلتفرم یکپارچه را به سند پایپ‌لاین اضافه کرد.
- شاهد مهم: وب‌سرویس پویا سه دسته دسترسی معرفی می‌کند: داده معاملاتی TSETMC، داده کدال و داده محاسباتی/نسبت‌های مالی؛ endpointها، راهنمای فراخوانی، نمونه کد و تعرفه‌ها در پنل معرفی شده‌اند.
- سند به‌روز: docs/BOURSEVIEW_CAPABILITY_PIPELINE.md
- کامیت آخر سند پایپ‌لاین: 5f9c16b9cb9883d106dda3ba0e799963434a126c
- تصمیم موقت: خرید API فعلاً انجام نشود؛ ابتدا قیمت/مجوز، endpointها، نمونه پاسخ، نرخ درخواست، تأخیر و کیفیت تاریخچه بررسی شود. مزیت API نسبت به دریافت مستقیم TSETMC باید با آزمون محدود سنجیده شود.
- گام بعدی: ممیزی data/tsetmc.py و تست‌های موجود در GitHub، سپس تکمیل ماتریس پوشش داده‌ها. هیچ کد LIVE اجرا یا تغییر داده نشده است.
