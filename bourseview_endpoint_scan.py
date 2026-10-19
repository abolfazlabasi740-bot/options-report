import urllib.request
import re

base = "https://www.bourseview.com"

files = [
"/static/js/2.280fdc27.chunk.js.map",
"/static/js/main.7bb20d27.chunk.js.map",
"/static/js/runtime~main.a8a9905a.js",
"/static/js/2.280fdc27.chunk.js",
"/static/js/main.7bb20d27.chunk.js",
]

patterns = re.compile(
r"""https?://[^"'\s<>]+"""
r"""|(?:https?://)?api[^"'\s<>]"""
r"""|/api/[^"'\s<>]"""
r"""|graphql"""
r"""|axios"""
r"""|fetch\s*("""
r"""|WebSocket""",
re.I
)

for path in files:
print("\n===== " + path + " =====")
try:
req = urllib.request.Request(
base + path,
headers={"User-Agent": "Mozilla/5.0"}
)
with urllib.request.urlopen(req, timeout=20) as response:
data = response.read().decode("utf-8", "replace")
print("HTTP_STATUS:", response.status)
print("CONTENT_LENGTH:", len(data))

        matches = list(dict.fromkeys(patterns.findall(data)))
        for item in matches[:100]:
            print(item[:500])

        if not matches:
            print("NO_ENDPOINT_PATTERN_FOUND")

except Exception as exc:
    print("ERROR:", repr(exc))

