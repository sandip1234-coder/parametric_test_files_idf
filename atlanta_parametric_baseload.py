from eppy.modeleditor import IDF
import os
import numpy as np

# idd path 
iddfile = r"C:\EnergyPlusV24-2-0\Energy+.idd"
IDF.setiddname(iddfile)

# my file here
idf_path = r"D:\Project\9_15_research\Python_Code"
# i will save here 
outdir = r"D:\Project\8_29_research\Atlanta_model\scaled_files"
os.makedirs(outdir, exist_ok=True)

FIELD_CANDIDATES = ["Watts_per_Zone_Floor_Area", "Watts_per_Floor_Area"]

def _is_watts_per_area_method(obj):
    method = getattr(obj, "Design_Level_Calculation_Method", "") or ""
    m = method.strip().lower()
    return ("w" in m and "area" in m)

def _set_scaled_value(obj, multiplier):
    """Scale Watts/Area field by multiplier."""
    for fname in FIELD_CANDIDATES:
        if hasattr(obj, fname):
            val = getattr(obj, fname)
            if val not in (None, "", "Autosize", "autocalculate", "AutoCalculate"):
                try:
                    f = float(val)
                except ValueError:
                    continue
                newval = f * multiplier
                setattr(obj, fname, newval)
                return fname, f, newval
    return None, None, None

# 1.1 to 2.5 at the step of 0.1 
for mult in np.arange(1.1, 2.51, 0.1):
    mult = round(mult, 1)  # avoid floating-point 2.5000001
    print(f"\nCreating {mult}x baseline ...")

    new_idf = IDF(idf_path)

    # Lights
    for lig in new_idf.idfobjects.get("LIGHTS", []):
        if _is_watts_per_area_method(lig):
            fname, old, new = _set_scaled_value(lig, mult)
            if fname:
                print(f"  [LIGHTS] {getattr(lig,'Name','(no name)')} | {fname}: {old} -> {new}")

    # ElectricEquipment
    for eq in new_idf.idfobjects.get("ELECTRICEQUIPMENT", []):
        if _is_watts_per_area_method(eq):
            fname, old, new = _set_scaled_value(eq, mult)
            if fname:
                print(f"  [EQUIP] {getattr(eq,'Name','(no name)')} | {fname}: {old} -> {new}")

    # Save with multiplier label (e.g., baseline_1.1x.idf)
    out_path = os.path.join(outdir, f"baseline_{mult}x.idf")
    new_idf.saveas(out_path)

print("\n Done. IDFs from 1.1x to 2.5x saved in:", outdir)
