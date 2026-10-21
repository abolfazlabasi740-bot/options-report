from pathlib import Path

p = Path("scripts/lmp_cards.py")
lines = p.read_text(encoding="utf-8").split("\n")
out = []
gate = disc = False

for i, line in enumerate(lines):
    out.append(line)
    # گیت قرنطینه پایه — بعد از "for c in cs:"
    if line.strip() == "for c in cs:" and not gate:
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if "_ref" not in nxt:
            out.append("        _u = str(c.get('underlying', ''))")
            out.append("        _b = float(c.get('base_closing') or 0)")
            out.append("        _ref = BASE_PLAUSIBLE.get(_u)")
            out.append("        if _ref and abs(_b - _ref) / _ref > 0.05:")
            out.append("            continue  # قرنطینه: پایه با منبع تأییدشده همخوان نیست")
            gate = True
    # تخفیف به ارزش ذاتی — بعد از خط حاشیه ایمنی
    if "حاشیه ایمنی" in line and "تخفیف" not in line and not disc:
        indent = line[: len(line) - len(line.lstrip())]
        out.append(indent + '''f"🎯 تخفیف به ارزش ذاتی: {_fmt(max((c.get('intrinsic_now') or 0) - (c.get('premium') or 0), 0))} ریال\\n"''')
        disc = True

p.write_text("\n".join(out), encoding="utf-8")
print(f"GATE={gate} DISCOUNT={disc}")
