import hashlib
import json
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path
from django.conf import settings


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def check_database(path, media):
    with closing(sqlite3.connect(path)) as db:
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("Database integrity check failed.")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Broken database relationships.")
        counts = {}
        for table in ("website_news", "website_product", "website_orderrequest", "auth_user"):
            counts[table] = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("website_news", "website_product"):
            for (image,) in db.execute(f"SELECT image FROM {table} WHERE image != ''"):
                target = (media / image).resolve()
                if not target.is_relative_to(media.resolve()) or not target.is_file():
                    raise ValueError("A referenced media file is missing.")
        return counts


def restore_archive(archive, destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError("Restore destination must not exist. Working data will not be overwritten.")
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or "manifest.json" not in names or "db.sqlite3" not in names:
            raise ValueError("Invalid backup archive.")
        for name in names:
            if not (destination / name).resolve().is_relative_to(destination):
                raise ValueError("Unsafe archive path.")
        manifest = json.loads(z.read("manifest.json"))
        if manifest.get("version") != 1 or set(names) != set(manifest["files"]) | {"manifest.json"}:
            raise ValueError("Invalid backup manifest.")
        destination.mkdir(parents=True)
        for name in names:
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with z.open(name) as source, path.open("xb") as target:
                import shutil
                shutil.copyfileobj(source, target)
    for name, checksum in manifest["files"].items():
        if digest(destination / name) != checksum:
            raise ValueError("Backup checksum mismatch.")
    counts = check_database(destination / "db.sqlite3", destination / "media")
    if counts != manifest["counts"]:
        raise ValueError("Restored record counts differ.")
    return counts


def create_backup(directory):
    from datetime import datetime, timezone
    import shutil
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    if settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3":
        raise ValueError("This backup command supports SQLite only.")
    database = Path(settings.DATABASES["default"]["NAME"]).resolve()
    if not database.is_file():
        raise ValueError("Database not found.")
    with tempfile.TemporaryDirectory(dir=directory) as work:
        work = Path(work)
        snapshot = work / "db.sqlite3"
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(snapshot)) as target:
                source.backup(target)
        media = work / "media"
        if settings.MEDIA_ROOT.exists():
            shutil.copytree(settings.MEDIA_ROOT, media)
        else:
            media.mkdir()
        counts = check_database(snapshot, media)
        files = [snapshot] + [p for p in media.rglob("*") if p.is_file()]
        manifest = {"version": 1, "counts": counts, "files": {
            p.relative_to(work).as_posix(): digest(p) for p in files}}
        archive = work / "archive.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for p in files:
                z.write(p, p.relative_to(work).as_posix())
            z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
        # Every backup is restored and checked before being published.
        restore_archive(archive, work / "verification")
        name = "pmk71-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".zip"
        result = directory / name
        archive.replace(result)
    return result, counts
