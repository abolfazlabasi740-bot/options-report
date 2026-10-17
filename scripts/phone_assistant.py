#!/usr/bin/env python3
import json, re, subprocess, sys, unicodedata

def norm(s):
    s = unicodedata.normalize("NFKC", str(s)).casefold()
    s = s.translate(str.maketrans({"ي": "ی", "ك": "ک", "ة": "ه", "ۀ": "ه"}))
    return "".join(c for c in s if c.isalnum())

if len(sys.argv) < 2:
    print("Usage: python scripts/phone_assistant.py NAME")
    raise SystemExit(2)

q = norm(" ".join(sys.argv[1:]))
try:
    r = subprocess.run(["termux-contact-list"], capture_output=True, text=True, timeout=20, check=True)
    contacts = json.loads(r.stdout)
except Exception as e:
    print("CONTACT_READ_ERROR:", e)
    raise SystemExit(1)

matches = []
seen = set()
for c in contacts if isinstance(contacts, list) else []:
    if not isinstance(c, dict):
        continue
    name = str(c.get("name", "")).strip()
    number = str(c.get("number", "")).strip()
    if q and q in norm(name) and re.fullmatch(r"[+0-9(). \-]+", number):
        if (name, number) not in seen:
            matches.append((name, number))
            seen.add((name, number))

if not matches:
    print("NO_MATCHING_CONTACTS:", " ".join(sys.argv[1:]))
    raise SystemExit(0)

for i, (name, number) in enumerate(matches, 1):
    print(f"{i}. {name} — {number}")

try:
    choice = input("شماره مخاطب؛ برای لغو 0: ").strip()
except (EOFError, KeyboardInterrupt):
    print("\nCANCELLED")
    raise SystemExit(0)

if not choice.isdigit() or not 1 <= int(choice) <= len(matches):
    print("CANCELLED")
    raise SystemExit(0)

name, number = matches[int(choice) - 1]
number = re.sub(r"[^+0-9]", "", number)
try:
    r = subprocess.run(["am", "start", "-a", "android.intent.action.DIAL", "-d", "tel:" + number],
                       capture_output=True, text=True, timeout=15)
    print("SELECTED_CONTACT:", name)
    print(r.stdout.strip())
    if r.stderr.strip():
        print(r.stderr.strip())
    if r.returncode:
        print("DIALER_OPEN_FAILED")
    else:
        print("شماره‌گیر باز شد؛ برای تماس، دکمه تماس را خودت بزن.")
except Exception as e:
    print("DIALER_ERROR:", e)
    raise SystemExit(1)
