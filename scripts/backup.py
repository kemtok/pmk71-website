import os
import sys
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
os.chdir(root)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
directory = root / "backups"
directory.mkdir(exist_ok=True)
with (directory / "backup.log").open("a", encoding="utf-8") as log:
    with redirect_stdout(log), redirect_stderr(log):
        print(datetime.now().isoformat(), "Starting backup", flush=True)
        try:
            import django
            django.setup()
            from django.core.management import call_command
            call_command("backup_site", no_color=True)
        except Exception:
            import traceback
            traceback.print_exc()
            sys.exit(1)
