# -*- coding: utf-8 -*-
from services.options_ranker import generate_options_message

async def options_command(update, context):
    status = await update.message.reply_text("⏳ در حال رتبه‌بندی اختیار...")
    try:
        text = generate_options_message()
        try:
            await status.edit_text(text)
        except Exception:
            await status.edit_text(text[:4000])
    except Exception as e:
        await status.edit_text(f"⚠️ خطا در دریافت داده: {type(e).__name__}")
