# tweak_imb_constructions_numbers_only.py
from io import StringIO
from pathlib import Path
from eppy.modeleditor import IDF

# ========= USER SETTINGS =========
IDD_PATH = r"C:\EnergyPlusV24-2-0\Energy+.idd"
INPUT_IDF = r"D:\Project\9_19_research\Parametric_test\Python_Code\Atlanta.idf"
U_MULTIPLIERS = [1.10, 1.20, 1.30, 1.40 , 1.50, 1.60, 1.70, 1.80, 1.90, 2.00]  # +10%, +20%, +50%, +100%
MIN_THICKNESS = 1e-5  # m floor for MATERIAL thickness
# Constructions to modify (names must match exactly in the IDF)
WALL_CONSTR = "Typical Insulated Metal Building Wall R-5.43"
ROOF_CONSTR = "Typical Insulated Metal Building Roof R-10.31"
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

def find_construction(idf, name):
    for c in idf.idfobjects.get("CONSTRUCTION", []):
        if cf(c.Name) == cf(name):
            return c
    return None

def construction_layer_fields(constr):
    fields = []
    if hasattr(constr, "Outside_Layer"):
        fields.append("Outside_Layer")
    for i in range(2, 11):
        f = f"Layer_{i}"
        if hasattr(constr, f):
            fields.append(f)
    return fields

def get_material_ref(idf, mat_name):
    """
    Return (type_key, obj) for a material name, or (None, None) if not found.
    type_key in {"MATERIAL", "MATERIAL:NOMASS", "MATERIAL:AIRGAP"}
    """
    if not mat_name: return (None, None)
    target = cf(mat_name)
    for key in ("MATERIAL", "MATERIAL:NOMASS", "MATERIAL:AIRGAP"):
        for m in idf.idfobjects.get(key, []):
            if cf(m.Name) == target:
                return (key, m)
    return (None, None)

def layer_R(idf, mat_name):
    """For reporting only (m2-K/W)."""
    tkey, m = get_material_ref(idf, mat_name)
    if not m: return None
    if tkey == "MATERIAL":
        # R = thickness / conductivity
        k = None
        for fld in ("Thermal_Conductivity", "Conductivity"):
            k = get_float(m, fld)
            if k is not None:
                break
        t = get_float(m, "Thickness")
        if k and t and k > 0.0:
            return t / k
        return None
    elif tkey in ("MATERIAL:NOMASS", "MATERIAL:AIRGAP"):
        return get_float(m, "Thermal_Resistance")
    return None

def construction_R(idf, constr):
    """Sum of layer R (no films), for reporting."""
    if not constr: return None
    Rsum, ok = 0.0, False
    for f in construction_layer_fields(constr):
        nm = getattr(constr, f, None)
        if not nm or str(nm).strip() == "": continue
        Ri = layer_R(idf, nm)
        if Ri is not None and Ri > 0.0:
            Rsum += Ri
            ok = True
            print(f"  Layer '{nm}': R = {Ri:.6f} m2-K/W")
    return Rsum if ok and Rsum > 0.0 else None

def scale_layer_numbers_in_place(idf, mat_name, u_mult):
    """
    Numbers-only edit:
      - MATERIAL:            Thickness /= u_mult (>= MIN_THICKNESS)
      - MATERIAL:NOMASS:     Thermal_Resistance /= u_mult
      - MATERIAL:AIRGAP:     Thermal_Resistance /= u_mult
    Keeps names identical.
    """
    tkey, m = get_material_ref(idf, mat_name)
    if not m: 
        print(f"    Skipped (material not found): {mat_name}")
        return

    if tkey == "MATERIAL":
        t = get_float(m, "Thickness")
        if t and t > 0.0:
            new_t = max(t / u_mult, MIN_THICKNESS)
            m.Thickness = new_t
            print(f"    MATERIAL: Thickness {t:.6f} -> {new_t:.6f} m  [{m.Name}]")
        else:
            print(f"    MATERIAL: no valid Thickness for [{m.Name}]")

    elif tkey in ("MATERIAL:NOMASS", "MATERIAL:AIRGAP"):
        R = get_float(m, "Thermal_Resistance")
        if R and R > 0.0:
            new_R = R / u_mult
            m.Thermal_Resistance = new_R
            print(f"    {tkey}: Thermal_Resistance {R:.6f} -> {new_R:.6f} m2-K/W  [{m.Name}]")
        else:
            print(f"    {tkey}: no valid Thermal_Resistance for [{m.Name}]")

def scale_construction_numbers_in_place(idf, constr_name, u_mult):
    """
    For a given construction, iterate its layers and scale the numbers in place
    on the referenced material objects. Names remain unchanged.
    """
    c = find_construction(idf, constr_name)
    if c is None:
        raise ValueError(f"Construction not found: {constr_name}")

    print(f"\nProcessing construction (numbers only): {constr_name}")
    R0 = construction_R(idf, c)
    U0 = (1.0 / R0) if (R0 and R0 > 0.0) else None
    if R0 and U0:
        print(f"Original R: {R0:.6f} m2-K/W, U: {U0:.6f} W/m2-K")
    else:
        print("Original R/U could not be calculated.")

    processed = 0
    for f in construction_layer_fields(c):
        nm = getattr(c, f, None)
        if not nm or str(nm).strip() == "": 
            continue
        processed += 1
        print(f"  Scaling layer field {f}: {nm}")
        scale_layer_numbers_in_place(idf, nm, u_mult)

    print(f"Scaled {processed} layers (numbers only).")

    R1 = construction_R(idf, c)
    U1 = (1.0 / R1) if (R1 and R1 > 0.0) else None
    if R1 and U1 and U0:
        print(f"New R: {R1:.6f} m2-K/W, U: {U1:.6f} W/m2-K  (x{U1 / U0:.2f} U-multiplier)")
    else:
        print("New R/U could not be calculated.")
    return U0, U1

def save_variant(idf, base_path, tag):
    out = base_path.with_name(f"{base_path.stem}_{tag}.idf")
    idf.saveas(str(out))
    return out

def main():
    print("Starting U-factor numbers-only modification process...")
    set_idd(IDD_PATH)

    in_path = Path(INPUT_IDF)
    if not in_path.exists():
        raise SystemExit(f"Input file not found: {in_path}")
    print(f"Loading IDF file: {in_path}")
    base = IDF(str(in_path))

    # Check constructions exist once
    for nm in (WALL_CONSTR, ROOF_CONSTR):
        if not find_construction(base, nm):
            raise SystemExit(f"Target construction missing: {nm}")
        print(f"Found construction: {nm}")

    # Run variants
    for u_mult in U_MULTIPLIERS:
        print("\n" + "=" * 60)
        print(f"Processing U-factor multiplier: {u_mult}")
        print("=" * 60)

        # Work on a copy of the whole IDF (but keep names same)
        work = IDF(StringIO(base.idfstr()))

        # Scale wall
        try:
            U0w, U1w = scale_construction_numbers_in_place(work, WALL_CONSTR, u_mult)
            if U0w and U1w:
                print(f"[WALL] U: {U0w:.6f} -> {U1w:.6f} W/m2-K (x{U1w / U0w:.2f})")
            else:
                print("[WALL] U-values not available after scaling.")
        except Exception as e:
            print(f"Error scaling wall construction: {e}")
            continue

        # Scale roof
        try:
            U0r, U1r = scale_construction_numbers_in_place(work, ROOF_CONSTR, u_mult)
            if U0r and U1r:
                print(f"[ROOF] U: {U0r:.6f} -> {U1r:.6f} W/m2-K (x{U1r / U0r:.2f})")
            else:
                print("[ROOF] U-values not available after scaling.")
        except Exception as e:
            print(f"Error scaling roof construction: {e}")
            continue

        # Save
        try:
            tag = f"Ux{str(u_mult).replace('.', 'p')}"
            out = save_variant(work, in_path, tag)
            print(f"Saved: {out}")
        except Exception as e:
            print(f"Error saving variant: {e}")
            continue

    print("\n" + "=" * 60)
    print("Done (numbers only, no renaming).")

if __name__ == "__main__":
    main()
