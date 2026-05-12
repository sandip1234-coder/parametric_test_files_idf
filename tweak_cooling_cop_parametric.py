# tweak_cooling_cop_parametric.py
from io import StringIO
from pathlib import Path
from eppy.modeleditor import IDF

# ========= USER SETTINGS =========
IDD_PATH  = r"C:\EnergyPlusV24-2-0\Energy+.idd"
INPUT_IDF = r"D:\Project\9_19_research\Parametric_test\Python_Code\Atlanta.idf"
# COP sweep: 3.0 -> 4.5 in 0.2 steps (inclusive of 4.5)
COP_START = 3.0
COP_STOP  = 4.5
COP_STEP  = 0.2
# =================================

def frange(start, stop, step):
    vals = []
    k = 0
    # include stop (with tiny tolerance)
    while start + k*step <= stop + 1e-9:
        vals.append(round(start + k*step, 3))
        k += 1
    # ensure exact stop is included
    if abs(vals[-1] - stop) > 1e-9:
        vals.append(stop)
    return vals

def cf(x): return (x or "").casefold()

def set_idd(path):
    IDF.setiddname(path)
    print(f"IDD file loaded: {path}")

def get_float(obj, field):
    if not hasattr(obj, field): return None
    v = getattr(obj, field)
    if v in ("", None, " "): return None
    try: return float(v)
    except: return None

def save_variant(idf, base_path, out_dir, tag):
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{base_path.stem}_cop_x{tag}.idf"
    idf.saveas(str(out))
    return out

def set_cooling_cop_in_place(idf, cop_value):
    """
    Numbers-only edit:
      - For every IDF object that exposes the field 'Gross_Rated_Cooling_COP',
        set that field to 'cop_value'.
      - Names remain unchanged.
    """
    total, changed = 0, 0
    print(f"\nSetting Gross_Rated_Cooling_COP = {cop_value:.3g} (W/W) wherever present")
    for key, objs in idf.idfobjects.items():
        for obj in objs:
            if hasattr(obj, "Gross_Rated_Cooling_COP"):
                total += 1
                old = get_float(obj, "Gross_Rated_Cooling_COP")
                setattr(obj, "Gross_Rated_Cooling_COP", cop_value)
                nm = getattr(obj, "Name", "<unnamed>")
                if old is None:
                    print(f"  [{key}] [{nm}] set from <blank> -> {cop_value:.6g}")
                else:
                    print(f"  [{key}] [{nm}] {old:.6g} -> {cop_value:.6g}")
                changed += 1
    if changed == 0:
        print("  No objects with 'Gross_Rated_Cooling_COP' found.")
    else:
        print(f"Updated {changed} object(s) with COP={cop_value:.3g}.")
    return changed

def main():
    print("Starting cooling COP parametric modification process...")
    set_idd(IDD_PATH)

    in_path = Path(INPUT_IDF)
    if not in_path.exists():
        raise SystemExit(f"Input file not found: {in_path}")
    print(f"Loading IDF file: {in_path}")
    base = IDF(str(in_path))

    # Prepare output directory
    out_dir = in_path.parent / "cooling_cop_parametric_idfs"
    print(f"Output directory: {out_dir}")

    # Build COP value list
    cop_values = frange(COP_START, COP_STOP, COP_STEP)
    print(f"COP sweep values: {cop_values}")

    # Create variants
    for cop in cop_values:
        print("\n" + "=" * 60)
        print(f"Processing COP: {cop:.1f} W/W")
        print("=" * 60)

        # Work on a copy of the whole IDF (names unchanged)
        work = IDF(StringIO(base.idfstr()))

        try:
            updated = set_cooling_cop_in_place(work, cop)
            tag = str(cop).replace(".", "p")
            out = save_variant(work, in_path, out_dir, tag)
            print(f"Saved ({updated} object(s) updated): {out}")
        except Exception as e:
            print(f"Error creating variant for COP={cop}: {e}")
            continue

    print("\n" + "=" * 60)
    print("Done (cooling COP sweep, 3.0 to 4.5, step 0.2).")

if __name__ == "__main__":
    main()
