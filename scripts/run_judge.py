"""Run the implication-gap judges against the live collector db (read-only) and write
verdicts to data/implied.sqlite (separate file, resumable). Usage:
  python scripts/run_judge.py [limit]   # limit = max judge calls this run (smoke test)"""
import sys, os, logging
sys.path.insert(0, ".")
try:
    from dotenv import load_dotenv; load_dotenv(".env")
except ImportError:
    pass
import yaml
from rb.db import DB
from rb.models import ModelClient
from rb.sources import Http
from rb import judge

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[logging.StreamHandler(), logging.FileHandler("data/judge.log")])
cfg = yaml.safe_load(open("config.yaml"))
http = Http()
models = [ModelClient(m, http) for m in (cfg.get("models") or []) if m.get("enabled", True)]
db = DB(os.path.join(cfg["run"].get("db", "data/resolvebench.sqlite")))
limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
print(judge.run(db, models, "data/implied.sqlite", limit=limit))
