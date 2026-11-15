"""Run the full offline analysis against a database snapshot.
Usage: python scripts/run_analysis.py [db_path] [out_dir] [explorer_url]
Numpy-only; safe to run on a copied snapshot while collection is live."""
import sys, time
sys.path.insert(0, ".")
from rb.db import DB
from rb import report, analysis, resolve

db_path = sys.argv[1] if len(sys.argv) > 1 else "data/snapshot.sqlite"
out_dir = sys.argv[2] if len(sys.argv) > 2 else "results"
explorer = sys.argv[3] if len(sys.argv) > 3 else "https://sepolia.basescan.org/tx/"

db = DB(db_path)
print(resolve.resolve(db, time.time()))          # fill any now-due outcomes in the copy
report.write(db, out_dir, explorer)
analysis.write(db, out_dir)
print("wrote", out_dir + "/report.md,", out_dir + "/analysis.md")
