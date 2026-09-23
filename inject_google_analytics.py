from pathlib import Path
import re

ROOT = Path("docs")
MEASUREMENT_ID = "G-SZLX21J9P2"

SNIPPET = f"""
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={MEASUREMENT_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{MEASUREMENT_ID}');
</script>
""".encode("utf-8")

updated = 0
already_present = 0
skipped = 0

for path in ROOT.rglob("*.html"):

    # Root index is only an immediate redirect; avoid double-counting visits.
    if path == ROOT / "index.html":
        skipped += 1
        continue

    data = path.read_bytes()

    if MEASUREMENT_ID.encode() in data:
        already_present += 1
        continue

    match = re.search(br"</head\s*>", data, flags=re.IGNORECASE)

    if not match:
        print(f"WARNING: no </head> found: {path}")
        skipped += 1
        continue

    new_data = data[:match.start()] + SNIPPET + data[match.start():]
    path.write_bytes(new_data)

    updated += 1
    print(f"Updated: {path}")

print()
print(f"Updated:         {updated}")
print(f"Already tagged: {already_present}")
print(f"Skipped:         {skipped}")
