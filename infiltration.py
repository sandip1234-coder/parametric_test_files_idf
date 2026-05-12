# tweak_infiltration_numbers_only.py
from io import StringIO
from pathlib import Path
from eppy.modeleditor import IDF

# ========= USER SETTINGS =========
IDD_PATH   = r"C:\EnergyPlusV24-2-0\Energy+.idd"
INPUT_IDF  = r"D:\Project\9_19_research\Parametric_test\Python_Code\Atlanta.idf"
# 0.10x ... 2.00x (0.10 step)
INFIL_MULTIPLIERS = [round(i/10, 2) for i in range(1, 21)]
# =================================

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
    out = out_dir / f"{base_path.stem}_infil_x{tag}.idf"
    idf.saveas(str(out))
    return out

def active_rate_field(zidr):
    """
    Determine which numeric field is active based on the
    Design_Flow_Rate_Calculation_Method. Returns (field_name, value) or (None, None).
    """
    # Common E+ methods:
    # "Flow/Zone", "AirChanges/Hour", "Flow/Area", "Flow/ExteriorArea", "Flow/ExteriorWallArea"
    method = getattr(zidr, "Design_Flow_Rate_Calculation_Method", "") or ""
    method_cf = cf(method)

    # Mapping from method to the numeric field that E+ uses
    method_to_field = {
        "flow/zone":                  "Design_Flow_Rate",
        "airchanges/hour":            "Air_Changes_per_Hour",
        "flow/area":                  "Flow_per_Zone_Floor_Area",
        "flow/exteriorarea":          "Flow_per_Exterior_Surface_Area",
        "flow/exteriorwallarea":      "Flow_per_Exterior_Wall_Area",
    }

    # If method is not specified, EnergyPlus may default to Design_Flow_Rate if present.
    if method_cf in method_to_field:
        fld = method_to_field[method_cf]
        return (fld, get_float(zidr, fld))

    # Fallback preference order if method is blank/unknown: use the first valid numeric
    for fld in ("Design_Flow_Rate",
                "Air_Changes_per_Hour",
                "Flow_per_Zone_Floor_Area",
                "Flow_per_Exterior_Surface_Area",
                "Flow_per_Exterior_Wall_Area"):
        val = get_float(zidr, fld)
        if val is not None:
            return (fld, val)

    return (None, None)

def scale_infiltration_numbers_in_place(idf, infil_mult):
    """
    Numbers-only edit:
      - For each ZoneInfiltration:DesignFlowRate object, detect the active numeric field
        (depending on the calculation method) and multiply it by 'infil_mult'.
      - Names remain unchanged.
    """
    objs = idf.idfobjects.get("ZONEINFILTRATION:DESIGNFLOWRATE", [])
    if not objs:
        print("No ZoneInfiltration:DesignFlowRate objects found.")
        return 0, 0

    touched, skipped = 0, 0
    print(f"\nScaling ZoneInfiltration:DesignFlowRate by x{infil_mult:.2f}")
    for z in objs:
        name = getattr(z, "Name", "<unnamed>")
        fld, val = active_rate_field(z)
        if fld and (val is not None):
            new_val = val * infil_mult
            setattr(z, fld, new_val)
            touched += 1
            print(f"  [{name}] {fld}: {val:.6g} -> {new_val:.6g}")
        else:
            skipped += 1
            print(f"  [{name}] Skipped (no active numeric field detected)")
    print(f"Scaled {touched} objects; skipped {skipped}.")
    return touched, skipped

def main():
    print("Starting infiltration numbers-only modification process...")
    set_idd(IDD_PATH)

    in_path = Path(INPUT_IDF)
    if not in_path.exists():
        raise SystemExit(f"Input file not found: {in_path}")
    print(f"Loading IDF file: {in_path}")
    base = IDF(str(in_path))

    # Prepare output directory
    out_dir = in_path.parent / "infiltration_parametric_idfs"
    print(f"Output directory: {out_dir}")

    # Run variants
    for mult in INFIL_MULTIPLIERS:
        print("\n" + "=" * 60)
        print(f"Processing infiltration multiplier: {mult:.2f}")
        print("=" * 60)

        # Work on a copy of the whole IDF (names unchanged)
        work = IDF(StringIO(base.idfstr()))

        try:
            scaled, skipped = scale_infiltration_numbers_in_place(work, mult)
            tag = str(mult).replace(".", "p")
            out = save_variant(work, in_path, out_dir, tag)
            print(f"Saved ({scaled} scaled, {skipped} skipped): {out}")
        except Exception as e:
            print(f"Error creating variant for x{mult}: {e}")
            continue

    print("\n" + "=" * 60)
    print("Done (infiltration numbers only, 0.10x to 2.00x).")

if __name__ == "__main__":
    main()
