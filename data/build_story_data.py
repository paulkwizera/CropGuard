"""
Builds frontend/assets/data/story.json from the AHS2024 microdata in data/Microdata/.

Run from the project root:   python data/build_story_data.py
Needs:                       pip install pandas

Only small, anonymous summary numbers are written to the JSON (no household IDs),
so the big .dta files never need to be served to browsers or committed to Git.
All figures are plain counts and shares of the surveyed households/plots (unweighted).
"""
import json
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent
MICRO = ROOT / "Microdata"
OUT = ROOT.parent / "frontend" / "assets" / "data" / "story.json"

CROP = next(MICRO.glob("AHS2024_Section3_4_*.dta"))
EXT = next(MICRO.glob("AHS2024_Section6_*.dta"))
HH = next(MICRO.glob("AHS2024_Section1_*.dta"))
S0 = MICRO / "AHS2024_Section0.dta"
SLOTS = range(1, 8)  # each plot record can hold up to 7 crops


def pct(part, whole, digits=1):
    return round(100 * part / whole, digits) if whole else None


# ------------------------------------------------------------------ crops (long format)
plot_cols = ["hhid", "province", "district", "Season", "s2q1", "s2q2", "s4_q1", "s4_q4", "s4_q12", "s4_q22"]
slot_cols = []
for k in SLOTS:
    slot_cols += [f"s3_q4_{k}", f"s3_q4_{k}a", f"s3_q9_{k}", f"s3q10_{k}", f"s3_q20_{k}", f"s2q23_{k}"]
raw = pd.read_stata(CROP, columns=plot_cols + slot_cols, convert_categoricals=True)
n_households = int(raw.hhid.nunique())
n_plot_records = len(raw)

frames = []
for k in SLOTS:
    f = raw[plot_cols[:6] + [f"s3_q4_{k}", f"s3_q4_{k}a", f"s3_q9_{k}", f"s3q10_{k}", f"s3_q20_{k}", f"s2q23_{k}"]].copy()
    f.columns = ["hhid", "province", "district", "season", "plot", "area_sqm", "crop", "prop", "seed", "seed_src", "harvest_kg", "change"]
    frames.append(f)
L = pd.concat(frames, ignore_index=True)
L = L[L.crop.notna()].copy()
for c in ("crop", "seed", "seed_src", "change", "province"):  # Stata labels carry stray trailing spaces
    L[c] = L[c].astype("string").str.strip()

result = {"source": "AHS2024 microdata", "households": n_households, "plot_records": n_plot_records, "crop_records": int(len(L))}

# ------------------------------------------------------------------ 1. what is grown
by_crop = L.groupby("crop").hhid.nunique().sort_values(ascending=False)
result["top_crops"] = [{"crop": c, "households": int(n), "share": pct(n, n_households)} for c, n in by_crop.head(10).items()]
maize_hh = int(by_crop.get("Maize", 0)); cass_hh = int(by_crop.get("Cassava", 0))
result["maize"] = {"households": maize_hh, "share": pct(maize_hh, n_households), "records": int((L.crop == "Maize").sum())}
result["cassava"] = {"households": cass_hh, "share": pct(cass_hh, n_households), "records": int((L.crop == "Cassava").sum())}
result["crop_rank"] = {"maize": int(list(by_crop.index).index("Maize") + 1), "cassava": int(list(by_crop.index).index("Cassava") + 1)}

# maize and cassava by province (share of that province's households)
s0 = pd.read_stata(S0, columns=["hhid", "province"], convert_categoricals=True).drop_duplicates("hhid")
prov_hh = s0.groupby("province").hhid.nunique()
crop_hh_prov = L.drop_duplicates("hhid").set_index("hhid").province
prov_hh_crop = crop_hh_prov.value_counts()
prov = []
for p in ["Kigali", "North", "South", "East", "West"]:
    n = int(prov_hh_crop.get(p, 0))
    m = int(L[(L.crop == "Maize") & (L.province == p)].hhid.nunique())
    c = int(L[(L.crop == "Cassava") & (L.province == p)].hhid.nunique())
    prov.append({"province": p, "farming_households": n, "maize": pct(m, n), "cassava": pct(c, n)})
result["by_province"] = prov

# ------------------------------------------------------------------ 2. seeds
def seed_split(df):
    s = df[df.seed.isin(["Traditional seeds", "Improved seeds", "1&2"])]
    n = len(s)
    return {
        "records": int(n),
        "traditional": pct((s.seed == "Traditional seeds").sum(), n),
        "improved": pct((s.seed == "Improved seeds").sum(), n),
        "both": pct((s.seed == "1&2").sum(), n),
    }
result["seeds"] = {"all": seed_split(L), "maize": seed_split(L[L.crop == "Maize"]), "cassava": seed_split(L[L.crop == "Cassava"])}
src = L[(L.crop == "Maize") & L.seed_src.notna()].seed_src.value_counts()
tot = int(src.sum())
result["maize_seed_sources"] = [{"source": s, "records": int(n), "share": pct(n, tot)} for s, n in src.items()]

# ------------------------------------------------------------------ 3. did production go up or down vs the previous season?
def change_split(df):
    c = df[df.change.isin(["Was highly decreased", "Was decreased", "No change", "Was increased", "Was highly increased"])]
    n = len(c)
    g = lambda label: pct((c.change == label).sum(), n)
    out = {"records": int(n), "highly_decreased": g("Was highly decreased"), "decreased": g("Was decreased"),
           "no_change": g("No change"), "increased": g("Was increased"), "highly_increased": g("Was highly increased")}
    out["down"] = round(out["highly_decreased"] + out["decreased"], 1)
    out["up"] = round(out["increased"] + out["highly_increased"], 1)
    return out
result["production_change"] = {"all": change_split(L), "maize": change_split(L[L.crop == "Maize"]), "cassava": change_split(L[L.crop == "Cassava"])}

# ------------------------------------------------------------------ 4. maize yield by seed type (median kg per hectare, plausible records only)
m = L[(L.crop == "Maize") & L.harvest_kg.notna() & L.area_sqm.notna() & L.prop.notna()].copy()
m["ha"] = m.area_sqm * m.prop / 100 / 10000
m = m[(m.ha > 0) & (m.harvest_kg > 0)]
m["yield_kg_ha"] = m.harvest_kg / m.ha
m = m[(m.yield_kg_ha > 50) & (m.yield_kg_ha < 15000)]  # drop impossible values (data-entry errors)
yy = {}
for label, key in (("Traditional seeds", "traditional"), ("Improved seeds", "improved")):
    s = m[m.seed == label].yield_kg_ha
    yy[key] = {"records": int(len(s)), "median_kg_ha": int(round(s.median())) if len(s) else None}
result["maize_yield"] = yy

# ------------------------------------------------------------------ 5. rain, inputs
plots = raw.drop_duplicates(["hhid", "s2q1", "Season"])
n_plots = len(plots)
irr = plots.s4_q22.astype(str).value_counts()
result["water"] = {
    "plots": int(n_plots),
    "irrigated": pct(irr.get("Yes", 0), n_plots),
    "no_water": pct(irr.get("No, there is no water available", 0), n_plots),
    "cannot_afford": pct(irr.get("No, I can't afford irrigation", 0), n_plots),
    "not_needed": pct(irr.get("No I don?t need irrigation", 0), n_plots),
}
result["inputs"] = {
    "plots": int(n_plots),
    "pesticide": pct((plots.s4_q12.astype(str) == "Yes").sum(), n_plots),
    "inorganic_fertilizer": pct((plots.s4_q4.astype(str) == "Yes").sum(), n_plots),
    "organic_fertilizer": pct((plots.s4_q1.astype(str) == "Yes").sum(), n_plots),
}

# ------------------------------------------------------------------ 6. advice and phones
e = pd.read_stata(EXT, columns=["hhid", "s6q1", "s6q4_1", "s6q8"], convert_categoricals=True)
e["s6q1"] = e.s6q1.astype(str)
e_hh = e.hhid.nunique()
got = e[e.s6q1 != "None"].hhid.nunique()
ipm = e[e.s6q1 == "Integrated pest management"].hhid.nunique()
wx = e[e.s6q1 == "Weather and climate information products/services"].hhid.nunique()
phone_src = e[e.s6q4_1.astype(str).str.startswith("Telephone")].hhid.nunique()
media_src = e[e.s6q4_1.astype(str).str.startswith("Media")].hhid.nunique()
ins = e[e.s6q8.astype(str) == "Yes"].hhid.nunique()
result["advice"] = {
    "households": int(e_hh),
    "any_service": pct(got, e_hh), "no_service": pct(e_hh - got, e_hh),
    "pest_management": pct(ipm, e_hh), "weather_info": pct(wx, e_hh),
    "via_phone_message": pct(phone_src, e_hh, 2), "via_phone_message_households": int(phone_src), "via_media": pct(media_src, e_hh),
    "crop_insurance": pct(ins, e_hh),
}
p = pd.read_stata(HH, columns=["hhid", "s4bq8", "s4bq10", "s4bq15"], convert_categoricals=True)
asked = p[p.s4bq8.notna()]
owners = asked[asked.s4bq8.astype(str) == "Yes"]
hh_any_phone = owners.hhid.nunique()
hh_asked = asked.hhid.nunique()
types = owners.s4bq10.astype(str).value_counts()
smart = int(types.get("Smart phone", 0) + types.get("Both type", 0)); typed = int(types.get("Basic phone", 0)) + smart
net = p[p.s4bq15.notna()]
result["phones"] = {
    "households": int(hh_asked),
    "household_has_phone": pct(hh_any_phone, hh_asked),
    "people_asked": int(len(asked)),
    "people_with_phone": pct(len(owners), len(asked)),
    "owners_with_smartphone": pct(smart, typed),
    "used_internet": pct((net.s4bq15.astype(str) == "Yes").sum(), len(net)),
}
result["seasons"] = {k: int(v) for k, v in raw.Season.astype(str).value_counts().items()}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", OUT)
print(json.dumps(result, ensure_ascii=False, indent=1))
