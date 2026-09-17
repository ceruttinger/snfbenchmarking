"""Build an auditable facility-year table from CMS renal HCRIS long files."""
from pathlib import Path
import csv, re
import pandas as pd

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw" / "renal_hcris_265_11"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

def locate(kind):
    pats = {"rpt": r"rpt", "nmrc": r"nmrc|numeric", "alpha": r"alph|alpha"}
    hits = [p for p in RAW.rglob("*") if p.is_file() and re.search(pats[kind], p.name, re.I)]
    if not hits: raise FileNotFoundError(f"No {kind} HCRIS file found under {RAW}")
    return max(hits, key=lambda p:p.stat().st_size)

def read_any(path):
    for sep in [",", "\t"]:
        try:
            x = pd.read_csv(path, sep=sep, dtype=str, low_memory=False)
            if x.shape[1] > 1: return x
        except Exception: pass
    return pd.read_csv(path, dtype=str, header=None, low_memory=False)

def normalize(x):
    x.columns = [str(c).strip().lower().replace(" ", "_") for c in x.columns]
    return x

def main():
    rpt, nmrc, alpha = map(locate, ["rpt","nmrc","alpha"])
    print("Report:", rpt); print("Numeric:", nmrc); print("Alpha:", alpha)
    r = normalize(read_any(rpt)); n = normalize(read_any(nmrc)); a = normalize(read_any(alpha))
    r.to_csv(OUT / "renal_report_file.csv", index=False)
    # Keep source long tables in parquet when possible; CSV fallback avoids a pyarrow requirement.
    try:
        n.to_parquet(OUT / "renal_numeric_long.parquet", index=False)
        a.to_parquet(OUT / "renal_alpha_long.parquet", index=False)
    except Exception:
        n.to_csv(OUT / "renal_numeric_long.csv", index=False)
        a.to_csv(OUT / "renal_alpha_long.csv", index=False)
    audit = pd.DataFrame({"table":["report","numeric","alpha"],"rows":[len(r),len(n),len(a)],"columns":[len(r.columns),len(n.columns),len(a.columns)]})
    audit.to_csv(OUT / "renal_ingestion_audit.csv", index=False)
    print(audit.to_string(index=False))
    print("Next: validate CMS-265-11 worksheet coordinates in metric_dictionary_dialysis.csv, then pivot selected metrics by report record number.")

if __name__ == "__main__": main()
