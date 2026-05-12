# tweak_dayinterval_setpoints.py
from pathlib import Path
from eppy.modeleditor import IDF

# ======= USER SETTINGS =======
IDD_PATH   = r"C:\EnergyPlusV24-2-0\Energy+.idd"
INPUT_IDF  = r"D:\Project\9_19_research\Parametric_test\Python_Code\Atlanta.idf"
OUT_DIR    = r"D:\Project\9_19_research\Parametric_test\Python_Code\cooling_setpoint_parametric_idfs"

TARGET_SCHEDULES = [
    "Automobile Cooling Setpoint",
    "Warehouse ClgSetp FineStorage Summer Design Day",
    "Warehouse ClgSetp FineStorage Winter Design Day"
]

F_START, F_STOP, F_STEP = 72, 82, 1   # sweep range in °F
# ==============================

def f_to_c(F): return (F - 32.0) * 5.0/9.0

def set_idd(path):
    IDF.setiddname(path)
    print(f"[OK] Loaded IDD: {path}")

def edit_dayinterval_schedule(sch, value_c):
    """Replace numeric values in a Schedule:Day:Interval object with value_c."""
    edits = 0
    for fld in sch.objls:
        if fld.lower().startswith("value"):
            try:
                float(getattr(sch, fld))
                setattr(sch, fld, f"{value_c:.6f}")
                edits += 1
            except:
                pass
    return edits

def save_variant(idf, out_dir: Path, temp_f: int):
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(INPUT_IDF).stem
    out_path = out_dir / f"{stem}_coolsp_{temp_f:02d}F.idf"
    idf.saveas(str(out_path))
    print(f"[SAVE] {out_path}")

def main():
    set_idd(IDD_PATH)

    for F in range(F_START, F_STOP + 1, F_STEP):
        C = f_to_c(F)
        idf = IDF(INPUT_IDF)

        total_edits = 0
        for sch in idf.idfobjects["SCHEDULE:DAY:INTERVAL"]:
            if sch.Name in TARGET_SCHEDULES:
                total_edits += edit_dayinterval_schedule(sch, C)

        if total_edits == 0:
            print(f"[WARN] {F}°F ({C:.4f}°C): no fields updated.")
        else:
            print(f"[INFO] {F}°F ({C:.4f}°C): updated {total_edits} values.")

        save_variant(idf, Path(OUT_DIR), F)

    print("\n[DONE] Cooling setpoint parametric IDFs generated.")

if __name__ == "__main__":
    main()
