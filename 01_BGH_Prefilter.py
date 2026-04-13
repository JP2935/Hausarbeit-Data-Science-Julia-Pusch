import re
import json
import shutil
import fitz
import pandas as pd
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

# =========================================================
# BGH PREFILTER V5
# - behält die inhaltlichen Verbesserungen
# - kein Review-Workflow
# - ausführlicher Output wie im alten Skript
# - optionaler sorted-Ordner
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
COURT_ROOT = BASE_DIR.parent / "Corona_Urteile" / "BGH"
OUT_DIR = BASE_DIR / "output"
OUT_DIR.mkdir(exist_ok=True)

# Wenn du für EuGH dieselbe Logik nutzen willst:
# 1. Datei z.B. in eugh_prefilter_v5.py umbenennen
# 2. COURT_ROOT = BASE_DIR / "EuGH" setzen
# 3. OUTPUT_PREFIX = "eugh"
OUTPUT_PREFIX = "bgh"

# ---------------------------------------------------------
# Optionen
# ---------------------------------------------------------
COPY_PDFS_TO_LABEL_FOLDERS = True
SORTED_DIR_NAME = "sorted"

EARLY_CHARS = 6000
EARLY_MULTIPLIER = 1.7

WEIGHT_TRIGGER = 2
WEIGHT_A = 5
WEIGHT_B = 3
WEIGHT_C = 1
WEIGHT_PHRASE = 6
WEIGHT_COOC = 2

THRESH_A = 12
THRESH_B = 6

ENABLE_STRICT_D = True
STRICT_D_MAX_TRIGGER_HITS = 1
STRICT_D_REQUIRE_NO_EARLY_TRIGGER = True

# ---------------------------------------------------------
# Suchmuster
# ---------------------------------------------------------
TRIGGERS = [
    r"\bcorona\b",
    r"\bcovid\b",
    r"\bcovid[-\s]?19\b",
    r"sars[-\s]?cov[-\s]?2",
    r"\bpandemie\b",
    r"\binfektionsschutzgesetz\b",
    r"\bifsg\b",
    r"\blockdown\b",
    r"\bquarant(?:ä|ae)ne\b",
    r"\bausgangsbeschr(?:ä|ae)nkung(?:en)?\b",
    r"\bkontaktbeschr(?:ä|ae)nkung(?:en)?\b",
    r"\b2g\b",
    r"\b3g\b",
    r"\bimpf\w*\b",
]

A_SIGNALS = [
    r"§\s*28a?\s*ifsg",
    r"\b28a\b.*\bifsg\b",
    r"\bschutzma(?:ß|ss)nahme(?:n)?\b",
    r"\buntersag(?:ung|en)\b",
    r"\bbetriebsschlie(?:ß|ss)ung(?:en)?\b",
    r"\bschlie(?:ß|ss)ungsanordnung(?:en)?\b",
    r"\bveranstaltungsverbot(?:e)?\b",
    r"\bkontaktverbot(?:e)?\b",
    r"\bmaskenpflicht\b",
    r"\btestpflicht\b",
    r"\bimpfpflicht\b",
    r"\bimpfschaden\b",
]

B_SIGNALS = [
    r"\bst(?:ö|oe)rung der gesch(?:ä|ae)ftsgrundlage\b",
    r"§\s*313\s*bgb",
    r"\bmiet(?:e|vertrag)\b",
    r"\bpacht\b",
    r"\bk(?:ü|ue)ndigung\b",
    r"\bleistungsst(?:ö|oe)rung\b",
    r"\bunm(?:ö|oe)glichkeit\b",
    r"§\s*275\s*bgb",
    r"\bverzug\b",
    r"§\s*286\s*bgb",
]

C_SIGNALS = [
    r"\bpandemiebedingt\b",
    r"\bcoronabedingt\b",
    r"\bwegen der corona[-\s]?pandemie\b",
    r"\bvideoverhandlung\b",
    r"\btelefonkonferenz\b",
    r"\bhygienekonzept\b",
    r"\bfristverl(?:ä|ae)ngerung\b",
]

PHRASES = [
    r"wegen der covid[-\s]?19[-\s]?pandemie",
    r"pandemiebedingte betriebsschlie",
    r"störung der geschäftsgrundlage.*pandemie",
    r"wegen der corona[-\s]?pandemie",
    r"aufgrund der corona[-\s]?pandemie",
    r"aufgrund der covid[-\s]?19[-\s]?pandemie",
]

GENERIC_B_TERMS = [
    r"\bmiet(?:e|vertrag)\b",
    r"\bpacht\b",
    r"\bk(?:ü|ue)ndigung\b",
    r"\bverzug\b",
    r"§\s*313\s*bgb",
    r"§\s*275\s*bgb",
    r"§\s*286\s*bgb",
]

# ---------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------
def extract_text(pdf_path: Path) -> str:
    try:
        doc = fitz.open(pdf_path)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text("text"))
        return "\n".join(text_parts).lower()
    except Exception:
        return ""

def count_patterns(patterns, text):
    total = 0
    detail = {}
    for p in patterns:
        hits = re.findall(p, text, flags=re.IGNORECASE)
        c = len(hits)
        if c > 0:
            detail[p] = c
            total += c
    return total, detail

def detail_to_string(detail_dict):
    if not detail_dict:
        return ""
    return "; ".join(f"{k}:{v}" for k, v in detail_dict.items())

def top_evidence_string(result_dict):
    parts = []
    if result_dict["trigger_hits"] > 0:
        parts.append(f"Trigger={result_dict['trigger_hits']}")
    if result_dict["a_hits"] > 0:
        parts.append(f"A={result_dict['a_hits']}")
    if result_dict["b_hits"] > 0:
        parts.append(f"B={result_dict['b_hits']}")
    if result_dict["c_hits"] > 0:
        parts.append(f"C={result_dict['c_hits']}")
    if result_dict["phrase_hits"] > 0:
        parts.append(f"Phrasen={result_dict['phrase_hits']}")
    if result_dict["cooc_bonus_hits"] > 0:
        parts.append(f"CoOcc={result_dict['cooc_bonus_hits']}")
    if result_dict["early_trigger_hits"] > 0 or result_dict["early_a_hits"] > 0:
        parts.append(
            f"Early(T={result_dict['early_trigger_hits']},A={result_dict['early_a_hits']})"
        )
    return " | ".join(parts)

def find_year_from_path(pdf_path: Path) -> str:
    for part in pdf_path.parts:
        if re.fullmatch(r"20\d{2}", part):
            return part
    return "unbekannt"

def generic_b_with_trigger_bonus(text: str, window: int = 250):
    """
    Bonus, wenn generische B-Begriffe in räumlicher Nähe zu Triggern vorkommen.
    Gibt auch Detailinfos für die Ausgabe zurück.
    """
    bonus = 0
    detail = Counter()

    trigger_positions = []
    for p in TRIGGERS:
        for m in re.finditer(p, text, flags=re.IGNORECASE):
            trigger_positions.append(m.start())

    if not trigger_positions:
        return bonus, {}

    for p in GENERIC_B_TERMS:
        local_hits = 0
        for m in re.finditer(p, text, flags=re.IGNORECASE):
            pos = m.start()
            if any(abs(pos - t) <= window for t in trigger_positions):
                bonus += 1
                local_hits += 1
        if local_hits > 0:
            detail[p] += local_hits

    return bonus, dict(detail)

def classify_document(text: str):
    early_text = text[:EARLY_CHARS]

    trigger_hits, trigger_detail = count_patterns(TRIGGERS, text)
    a_hits, a_detail = count_patterns(A_SIGNALS, text)
    b_hits, b_detail = count_patterns(B_SIGNALS, text)
    c_hits, c_detail = count_patterns(C_SIGNALS, text)
    phrase_hits, phrase_detail = count_patterns(PHRASES, text)

    early_trigger_hits, early_trigger_detail = count_patterns(TRIGGERS, early_text)
    early_a_hits, early_a_detail = count_patterns(A_SIGNALS, early_text)

    cooc_bonus_hits, cooc_detail = generic_b_with_trigger_bonus(text)

    base_score = (
        trigger_hits * WEIGHT_TRIGGER +
        a_hits * WEIGHT_A +
        b_hits * WEIGHT_B +
        c_hits * WEIGHT_C +
        phrase_hits * WEIGHT_PHRASE +
        cooc_bonus_hits * WEIGHT_COOC
    )

    early_score = (
        early_trigger_hits * WEIGHT_TRIGGER +
        early_a_hits * WEIGHT_A
    )

    final_score = base_score + (EARLY_MULTIPLIER - 1.0) * early_score

    if ENABLE_STRICT_D:
        if (
            trigger_hits <= STRICT_D_MAX_TRIGGER_HITS
            and a_hits == 0 and b_hits == 0 and c_hits == 0 and phrase_hits == 0
            and cooc_bonus_hits == 0
            and (not STRICT_D_REQUIRE_NO_EARLY_TRIGGER or early_trigger_hits == 0)
        ):
            label = "D"
        elif final_score >= THRESH_A and a_hits > 0:
            label = "A"
        elif final_score >= THRESH_B:
            label = "B"
        elif trigger_hits > 0 or c_hits > 0:
            label = "C"
        else:
            label = "D"
    else:
        if final_score >= THRESH_A and a_hits > 0:
            label = "A"
        elif final_score >= THRESH_B:
            label = "B"
        elif trigger_hits > 0 or c_hits > 0:
            label = "C"
        else:
            label = "D"

    return {
        "label": label,
        "base_score": round(base_score, 2),
        "early_score": round(early_score, 2),
        "final_score": round(final_score, 2),
        "trigger_hits": trigger_hits,
        "a_hits": a_hits,
        "b_hits": b_hits,
        "c_hits": c_hits,
        "phrase_hits": phrase_hits,
        "cooc_bonus_hits": cooc_bonus_hits,
        "early_trigger_hits": early_trigger_hits,
        "early_a_hits": early_a_hits,
        "trigger_detail": trigger_detail,
        "a_detail": a_detail,
        "b_detail": b_detail,
        "c_detail": c_detail,
        "phrase_detail": phrase_detail,
        "cooc_detail": cooc_detail,
        "early_trigger_detail": early_trigger_detail,
        "early_a_detail": early_a_detail,
    }

def ensure_sorted_dirs(sorted_root: Path):
    for label in ["A", "B", "C", "D", "ERROR"]:
        (sorted_root / label).mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------
def main():
    run_timestamp = datetime.now().isoformat(timespec="seconds")
    pdfs = sorted(COURT_ROOT.rglob("*.pdf"))

    rows = []
    errors = []
    label_counter = Counter()
    year_counter = Counter()
    label_year_counter = defaultdict(Counter)

    sorted_root = OUT_DIR / SORTED_DIR_NAME
    if COPY_PDFS_TO_LABEL_FOLDERS:
        ensure_sorted_dirs(sorted_root)

    for pdf in pdfs:
        year = find_year_from_path(pdf)
        text = extract_text(pdf)

        if not text.strip():
            errors.append(str(pdf))
            if COPY_PDFS_TO_LABEL_FOLDERS:
                try:
                    shutil.copy2(pdf, sorted_root / "ERROR" / pdf.name)
                except Exception:
                    pass
            continue

        result = classify_document(text)
        label = result["label"]

        label_counter[label] += 1
        year_counter[year] += 1
        label_year_counter[year][label] += 1

        if COPY_PDFS_TO_LABEL_FOLDERS:
            try:
                shutil.copy2(pdf, sorted_root / label / pdf.name)
            except Exception:
                pass

        rows.append({
            "file": pdf.name,
            "path": str(pdf),
            "year": year,
            "label": label,
            "base_score": result["base_score"],
            "early_score": result["early_score"],
            "final_score": result["final_score"],
            "trigger_hits": result["trigger_hits"],
            "a_hits": result["a_hits"],
            "b_hits": result["b_hits"],
            "c_hits": result["c_hits"],
            "phrase_hits": result["phrase_hits"],
            "cooc_bonus_hits": result["cooc_bonus_hits"],
            "early_trigger_hits": result["early_trigger_hits"],
            "early_a_hits": result["early_a_hits"],
            "evidence_trigger": detail_to_string(result["trigger_detail"]),
            "evidence_A": detail_to_string(result["a_detail"]),
            "evidence_B": detail_to_string(result["b_detail"]),
            "evidence_C": detail_to_string(result["c_detail"]),
            "evidence_phrases": detail_to_string(result["phrase_detail"]),
            "evidence_cooc": detail_to_string(result["cooc_detail"]),
            "evidence_early_trigger": detail_to_string(result["early_trigger_detail"]),
            "evidence_early_A": detail_to_string(result["early_a_detail"]),
            "evidence_top": top_evidence_string(result),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        print("Keine auswertbaren PDFs gefunden.")
        return

    # -----------------------------------------------------
    # Dateien speichern
    # -----------------------------------------------------
    labels_csv = OUT_DIR / f"{OUTPUT_PREFIX}_labels.csv"
    distribution_csv = OUT_DIR / f"{OUTPUT_PREFIX}_label_distribution.csv"
    by_year_csv = OUT_DIR / f"{OUTPUT_PREFIX}_labels_by_year.csv"
    score_summary_csv = OUT_DIR / f"{OUTPUT_PREFIX}_score_summary_by_label.csv"
    summary_txt = OUT_DIR / "run_summary.txt"
    config_json = OUT_DIR / "run_config.json"

    df.to_csv(labels_csv, index=False, encoding="utf-8")

    distribution_df = (
        df["label"]
        .value_counts()
        .rename_axis("label")
        .reset_index(name="count")
    )
    distribution_df["percent"] = (distribution_df["count"] / len(df) * 100).round(1)
    distribution_df = distribution_df.sort_values("label")
    distribution_df.to_csv(distribution_csv, index=False, encoding="utf-8")

    by_year_df = (
        df.pivot_table(index="year", columns="label", values="file", aggfunc="count", fill_value=0)
        .reset_index()
    )
    by_year_df.to_csv(by_year_csv, index=False, encoding="utf-8")

    score_summary_df = (
        df.groupby("label")[["base_score", "early_score", "final_score"]]
        .mean()
        .round(2)
        .reset_index()
        .sort_values("label")
    )
    score_summary_df.to_csv(score_summary_csv, index=False, encoding="utf-8")

    config = {
        "run_timestamp": run_timestamp,
        "COURT_ROOT": str(COURT_ROOT),
        "OUTPUT_PREFIX": OUTPUT_PREFIX,
        "COPY_PDFS_TO_LABEL_FOLDERS": COPY_PDFS_TO_LABEL_FOLDERS,
        "SORTED_DIR_NAME": SORTED_DIR_NAME,
        "EARLY_CHARS": EARLY_CHARS,
        "EARLY_MULTIPLIER": EARLY_MULTIPLIER,
        "weights": {
            "WEIGHT_TRIGGER": WEIGHT_TRIGGER,
            "WEIGHT_A": WEIGHT_A,
            "WEIGHT_B": WEIGHT_B,
            "WEIGHT_C": WEIGHT_C,
            "WEIGHT_PHRASE": WEIGHT_PHRASE,
            "WEIGHT_COOC": WEIGHT_COOC,
        },
        "thresholds": {
            "THRESH_A": THRESH_A,
            "THRESH_B": THRESH_B,
        },
        "strict_D": {
            "ENABLE_STRICT_D": ENABLE_STRICT_D,
            "STRICT_D_MAX_TRIGGER_HITS": STRICT_D_MAX_TRIGGER_HITS,
            "STRICT_D_REQUIRE_NO_EARLY_TRIGGER": STRICT_D_REQUIRE_NO_EARLY_TRIGGER,
        },
        "keyword_lists": {
            "TRIGGERS": TRIGGERS,
            "A_SIGNALS": A_SIGNALS,
            "B_SIGNALS": B_SIGNALS,
            "C_SIGNALS": C_SIGNALS,
            "PHRASES": PHRASES,
            "GENERIC_B_TERMS": GENERIC_B_TERMS,
        },
    }
    with open(config_json, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    # -----------------------------------------------------
    # Lesbare Summary
    # -----------------------------------------------------
    lines = []
    lines.append(f"Run: {run_timestamp}")
    lines.append(f"Root: {COURT_ROOT}")
    lines.append(f"PDFs processed: {len(df)}")
    lines.append(f"Errors: {len(errors)}")
    lines.append("")
    lines.append("Label counts:")
    for label in ["A", "B", "C", "D"]:
        lines.append(f"{label}: {label_counter.get(label, 0)}")
    lines.append("")
    lines.append("Label percentages:")
    for label in ["A", "B", "C", "D"]:
        count = label_counter.get(label, 0)
        pct = round(count / len(df) * 100, 1) if len(df) else 0.0
        lines.append(f"{label}: {pct}%")
    lines.append("")
    lines.append("Average scores by label:")
    for _, row in score_summary_df.iterrows():
        lines.append(
            f"{row['label']}: base={row['base_score']}, early={row['early_score']}, final={row['final_score']}"
        )
    lines.append("")
    lines.append("Counts by year:")
    for year in sorted(year_counter):
        lines.append(f"{year}: {year_counter[year]}")
    lines.append("")
    lines.append("Counts by year and label:")
    for year in sorted(label_year_counter):
        parts = []
        for label in ["A", "B", "C", "D"]:
            parts.append(f"{label}={label_year_counter[year].get(label, 0)}")
        lines.append(f"{year}: " + ", ".join(parts))
    lines.append("")
    lines.append("Output files:")
    lines.append(f"- Labels CSV: {labels_csv}")
    lines.append(f"- Distribution CSV: {distribution_csv}")
    lines.append(f"- By-year CSV: {by_year_csv}")
    lines.append(f"- Score summary CSV: {score_summary_csv}")
    lines.append(f"- Config JSON: {config_json}")
    if COPY_PDFS_TO_LABEL_FOLDERS:
        lines.append(f"- Sorted folder: {sorted_root}")
    if errors:
        lines.append("")
        lines.append("Files with errors:")
        lines.extend(errors)

    with open(summary_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n".join(lines))

if __name__ == "__main__":
    main()
