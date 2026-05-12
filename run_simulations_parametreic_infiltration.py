# run_all_idfs_keep_tables_and_csv.py
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

# ========= USER SETTINGS =========
ENERGYPLUS_EXE = r"C:\EnergyPlusV24-2-0\energyplus.exe"
EPW_PATH = r"D:\DownLoads\weather Files\USA_GA_Atlanta-Hartsfield-Jackson.Intl.AP.722190_TMY3\USA_GA_Atlanta-Hartsfield-Jackson.Intl.AP.722190_TMY3.epw"
IDF_DIR = r"D:\Project\9_19_research\Parametric_test\Python_Code\infiltration_parametric_idfs"
# Where to save the final kept files (defaults to IDF_DIR). Change if you want another folder.
OUTPUT_DIR = IDF_DIR
# Add extra E+ flags if you like:
EXTRA_FLAGS = ["--readvars", "--expandobjects"]
# =================================

def run_energyplus(idf_path: Path, run_dir: Path) -> int:
    """Run EnergyPlus for a single IDF into run_dir. Return process return code."""
    cmd = [
        ENERGYPLUS_EXE,
        "--weather", EPW_PATH,
        "--output-directory", str(run_dir),
    ] + EXTRA_FLAGS + [str(idf_path)]
    print(f"\n>>> Running: {idf_path.name}")
    print(">>> Cmd:", " ".join(f'"{c}"' if " " in c else c for c in cmd))
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        # Echo E+ output (helpful for debugging)
        print(proc.stdout)
        return proc.returncode
    except FileNotFoundError:
        print("!! EnergyPlus executable not found at:", ENERGYPLUS_EXE)
        return 127

def keep_only_csv_and_table(run_dir: Path, base_name: str, out_dir: Path) -> bool:
    """
    Move eplusout.csv -> <base_name>.csv
         eplustbl.pdf -> <base_name>Table.pdf  (preferred)
    If no PDF, try eplustbl.htm -> <base_name>Table.htm
    Delete everything else in run_dir. Return True if at least CSV moved.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_src = run_dir / "eplusout.csv"
    pdf_src = run_dir / "eplustbl.pdf"
    htm_src = run_dir / "eplustbl.htm"

    kept_any = False

    # CSV
    if csv_src.exists():
        csv_dst = out_dir / f"{base_name}.csv"
        shutil.move(str(csv_src), str(csv_dst))
        print(f"  Kept CSV: {csv_dst.name}")
        kept_any = True
    else:
        print("  Warning: eplusout.csv not found; no CSV kept.")

    # Table (PDF preferred)
    if pdf_src.exists():
        pdf_dst = out_dir / f"{base_name}Table.pdf"
        shutil.move(str(pdf_src), str(pdf_dst))
        print(f"  Kept Table PDF: {pdf_dst.name}")
    elif htm_src.exists():
        htm_dst = out_dir / f"{base_name}Table.htm"
        shutil.move(str(htm_src), str(htm_dst))
        print(f"  Kept Table HTML (no PDF produced): {htm_dst.name}")
    else:
        print("  Warning: No eplustbl.pdf or eplustbl.htm found; no Table kept.")

    # Remove all other files in run_dir
    for p in run_dir.glob("*"):
        try:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink(missing_ok=True)
        except Exception as e:
            print(f"  Note: could not delete {p.name}: {e}")

    return kept_any

def main():
    idf_dir = Path(IDF_DIR)
    out_dir = Path(OUTPUT_DIR)
    epw = Path(EPW_PATH)
    eplus = Path(ENERGYPLUS_EXE)

    # Basic checks
    if not eplus.exists():
        print(f"EnergyPlus not found at: {eplus}")
        sys.exit(2)
    if not epw.exists():
        print(f"EPW not found at: {epw}")
        sys.exit(2)
    if not idf_dir.exists():
        print(f"IDF folder not found: {idf_dir}")
        sys.exit(2)

    idfs = sorted([p for p in idf_dir.glob("*.idf")])
    if not idfs:
        print(f"No IDF files found in {idf_dir}")
        sys.exit(0)

    print(f"Found {len(idfs)} IDF(s) to run in: {idf_dir}")
    successes, failures = 0, 0

    for idf in idfs:
        base_name = idf.stem  # e.g., "Atlanta_infil_x0p1"
        with TemporaryDirectory(prefix=f"eplus_{base_name}_") as tmp:
            run_dir = Path(tmp)
            rc = run_energyplus(idf, run_dir)
            if rc != 0:
                print(f"!! EnergyPlus failed for {idf.name} (exit code {rc}). Skipping keep/cleanup copy.")
                failures += 1
                continue

            kept = keep_only_csv_and_table(run_dir, base_name, out_dir)
            if kept:
                successes += 1
            else:
                # Still count as success if sim ran, but warn if nothing to keep
                print(f"  Note: Simulation ran for {idf.name} but no CSV was kept.")
                successes += 1

    print(f"\nAll done. Successful runs: {successes}, Failed runs: {failures}")

if __name__ == "__main__":
    main()
