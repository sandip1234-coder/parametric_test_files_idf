# run_parametric_folders_keep_tables_and_csv.py
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

# ========= USER SETTINGS =========
ENERGYPLUS_EXE = r"C:\EnergyPlusV24-2-0\energyplus.exe"
EPW_PATH = r"D:\DownLoads\weather Files\USA_GA_Atlanta-Hartsfield-Jackson.Intl.AP.722190_TMY3\USA_GA_Atlanta-Hartsfield-Jackson.Intl.AP.722190_TMY3.epw"

# Add any number of folders here:
IDF_DIRS = [
   
    r"D:\Project\9_19_research\Parametric_test\Python_Code\cooling_cop_parametric_idfs"]

# If None, saves into each folder itself; otherwise set a single output folder:
OUTPUT_DIR = None

# Extra EnergyPlus flags:
EXTRA_FLAGS = ["--readvars", "--expandobjects"]
# =================================

def run_energyplus(idf_path: Path, run_dir: Path) -> int:
    cmd = [
        ENERGYPLUS_EXE,
        "--weather", EPW_PATH,
        "--output-directory", str(run_dir),
    ] + EXTRA_FLAGS + [str(idf_path)]
    print(f"\n>>> Running: {idf_path}")
    print(">>> Cmd:", " ".join(f'"{c}"' if " " in c else c for c in cmd))
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        print(proc.stdout)
        return proc.returncode
    except FileNotFoundError:
        print("!! EnergyPlus executable not found at:", ENERGYPLUS_EXE)
        return 127

def keep_only_csv_and_table(run_dir: Path, base_name: str, out_dir: Path) -> bool:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_src = run_dir / "eplusout.csv"
    pdf_src = run_dir / "eplustbl.pdf"
    htm_src = run_dir / "eplustbl.htm"

    kept_any = False

    if csv_src.exists():
        csv_dst = out_dir / f"{base_name}.csv"
        shutil.move(str(csv_src), str(csv_dst))
        print(f"  Kept CSV: {csv_dst}")
        kept_any = True
    else:
        print("  Warning: eplusout.csv not found; no CSV kept.")

    if pdf_src.exists():
        pdf_dst = out_dir / f"{base_name}Table.pdf"
        shutil.move(str(pdf_src), str(pdf_dst))
        print(f"  Kept Table PDF: {pdf_dst}")
    elif htm_src.exists():
        htm_dst = out_dir / f"{base_name}Table.htm"
        shutil.move(str(htm_src), str(htm_dst))
        print(f"  Kept Table HTML: {htm_dst}")
    else:
        print("  Warning: No eplustbl.pdf or eplustbl.htm found; no Table kept.")

    # Clean up everything else from the temp run folder
    for p in run_dir.glob("*"):
        try:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink(missing_ok=True)
        except Exception as e:
            print(f"  Note: could not delete {p.name}: {e}")

    return kept_any

def run_folder(idf_dir: Path, output_dir_override: Path | None) -> tuple[int, int]:
    if not idf_dir.exists():
        print(f"Folder not found, skipping: {idf_dir}")
        return (0, 0)

    idfs = sorted(idf_dir.glob("*.idf"))
    if not idfs:
        print(f"No IDF files found in {idf_dir}")
        return (0, 0)

    print(f"\n=== Folder: {idf_dir} | {len(idfs)} IDF(s) ===")
    successes = failures = 0

    for idf in idfs:
        base_name = idf.stem   # e.g., Atlanta_cop_x3p0
        out_dir = output_dir_override if output_dir_override else idf_dir

        with TemporaryDirectory(prefix=f"eplus_{base_name}_") as tmp:
            run_dir = Path(tmp)
            rc = run_energyplus(idf, run_dir)
            if rc != 0:
                print(f"!! EnergyPlus failed for {idf.name} (exit code {rc}).")
                failures += 1
                continue

            kept = keep_only_csv_and_table(run_dir, base_name, out_dir)
            if kept:
                successes += 1
            else:
                # Simulation ran, but no CSV kept; still count as success
                print(f"  Note: Simulation ran for {idf.name} but no CSV was kept.")
                successes += 1

    return (successes, failures)

def main():
    eplus = Path(ENERGYPLUS_EXE)
    epw = Path(EPW_PATH)
    if not eplus.exists():
        print(f"EnergyPlus not found at: {eplus}")
        sys.exit(2)
    if not epw.exists():
        print(f"EPW not found at: {epw}")
        sys.exit(2)

    total_ok = total_fail = 0
    out_override = Path(OUTPUT_DIR) if OUTPUT_DIR else None

    for folder in IDF_DIRS:
        ok, fail = run_folder(Path(folder), out_override)
        total_ok  += ok
        total_fail += fail

    print(f"\nAll done. Successful runs: {total_ok}, Failed runs: {total_fail}")

if __name__ == "__main__":
    main()
