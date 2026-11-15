"""Generate report figures from a db snapshot. Needs matplotlib (not in the frozen
requirements): run with the analysis venv. Usage: python scripts/make_figures.py [db] [out_dir]"""
import sys
sys.path.insert(0, ".")
from rb.db import DB
from rb import figures
db = DB(sys.argv[1] if len(sys.argv) > 1 else "data/snapshot.sqlite")
print("wrote", figures.make_all(db, sys.argv[2] if len(sys.argv) > 2 else "results"))
