# Termux Relay v1

## هدف
اجرای فرمان‌های کوچک روی Termux بدون انتقال Snapshot یا پروژه از مسیر Git.

## معماری
ChatGPT/GitHub -> command queue -> Termux relay -> local execution -> compact evidence -> GitHub result.

## قرارداد
- command_id یکتا
- argv به‌صورت آرایه، بدون shell operators
- cwd فقط داخل OptimusAI_V41_LIVE
- خروجی محدود و هش‌شده
- timeout اجباری
- نتیجه شامل status/exit_code/stdout/stderr_sha256/started_at/finished_at

## نکته عملی
Relay روی خود Termux باید به‌صورت process دائمی فعال باشد. GitHub فقط control-plane و evidence store است؛ داده بازار از این مسیر عبور نمی‌کند.

## وضعیت
نسخه معماری آماده است؛ فعال‌سازی واقعی منوط به اجرای relay process روی Termux است.
