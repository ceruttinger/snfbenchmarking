"""Download and extract CMS-265-11 renal HCRIS data.

CMS distributes renal HCRIS as one ZIP containing all fiscal years. The exact
ZIP URL can change with CMS releases, so the script discovers candidate ZIP
links from the CMS renal cost-report page unless RENAL_HCRIS_ZIP is supplied.
"""
from pathlib import Path
import os, re, zipfile
import requests
from bs4 import BeautifulSoup

CMS_PAGE = os.getenv("RENAL_HCRIS_PAGE", "https://www.cms.gov/data-research/statistics-trends-and-reports/cost-reports")
OUT = Path(__file__).parent / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

def discover_zip():
    override = os.getenv("RENAL_HCRIS_ZIP")
    if override:
        return override
    html = requests.get(CMS_PAGE, timeout=60).text
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    for a in soup.find_all("a", href=True):
        text = (a.get_text(" ", strip=True) + " " + a["href"]).lower()
        if ("renal" in text or "rnl" in text or "265-11" in text) and ("zip" in text or ".zip" in text):
            href = a["href"]
            if href.startswith("/"):
                href = "https://www.cms.gov" + href
            candidates.append(href)
    if not candidates:
        raise RuntimeError("Could not discover the CMS renal HCRIS ZIP. Set RENAL_HCRIS_ZIP to the current CMS download URL.")
    return candidates[0]

def main():
    url = discover_zip()
    print("Renal HCRIS source:", url)
    zpath = OUT / "renal_hcris_265_11.zip"
    with requests.get(url, stream=True, timeout=180) as r:
        r.raise_for_status()
        with zpath.open("wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                f.write(chunk)
    extract = OUT / "renal_hcris_265_11"
    extract.mkdir(exist_ok=True)
    with zipfile.ZipFile(zpath) as z:
        z.extractall(extract)
    files = sorted(str(p.relative_to(OUT)) for p in extract.rglob("*") if p.is_file())
    (OUT / "renal_manifest.txt").write_text("source=" + url + "\n" + "\n".join(files))
    print(f"Extracted {len(files)} files to {extract}")

if __name__ == "__main__":
    main()
