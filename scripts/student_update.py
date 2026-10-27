"""Public aigo-learning updater: stdlib, 3h throttle, staged integrity and rollback."""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

REPOSITORY = "AI-GO-APP/aigo-learning-skill"
INTERVAL = 3 * 60 * 60
MAX_ARCHIVE = 40 * 1024 * 1024


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "aigo-learning-updater", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=10) as response:
        data = response.read(MAX_ARCHIVE + 1)
    if len(data) > MAX_ARCHIVE:
        raise ValueError("下載超過學生套件大小限制")
    return data


def development_copy(root: Path) -> bool:
    if not (root / ".git").exists():
        return False
    try:
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=root, stderr=subprocess.DEVNULL).decode().strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=root, stderr=subprocess.DEVNULL).strip()
        return branch not in {"main", "master"} or bool(dirty)
    except (OSError, subprocess.CalledProcessError):
        return True


def state_path(root: Path) -> Path:
    key = hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:24]
    return Path.home() / ".aigo-learning" / "updates" / f"{key}.json"


def save_state(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".state-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def atomic_write(path: Path, value: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".update-")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(value)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def safe_name(name: str) -> None:
    rel = PurePosixPath(name)
    if rel.is_absolute() or ".." in rel.parts or "\\" in name or ":" in name or name.startswith("."):
        raise ValueError("更新清單路徑不安全")
    if rel.parts[0] not in {"scripts", "references", "technical", "exercises", "assets"} and name not in {
            "SKILL.md", "VERSION", "README.md", "LICENSE", "UPSTREAM.json"}:
        raise ValueError("更新超出技能檔案範圍")


def stage_archive(data: bytes, target: Path) -> dict:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.namelist()
        if not members or len(members) != len(set(members)):
            raise ValueError("更新壓縮檔清單無效")
        roots = {PurePosixPath(name).parts[0] for name in members if PurePosixPath(name).parts}
        if len(roots) != 1:
            raise ValueError("更新壓縮檔根目錄無效")
        prefix = roots.pop() + "/"
        if sum(info.file_size for info in archive.infolist()) > MAX_ARCHIVE:
            raise ValueError("解壓後超過學生套件大小限制")
        manifest_data = archive.read(prefix + "PACKAGE.json")
        meta = json.loads(manifest_data)
        if not isinstance(meta, dict) or meta.get("skill") != "aigo-learning" or not isinstance(meta.get("files"), dict):
            raise ValueError("更新清單不是學生技能")
        if not meta["files"] or not {"SKILL.md", "VERSION", "scripts/check_update.py", "scripts/student_update.py"} <= set(meta["files"]):
            raise ValueError("更新缺少必要技能檔案")
        for name, expected in meta["files"].items():
            safe_name(name)
            info = archive.getinfo(prefix + name)
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("更新壓縮檔不能含符號連結")
            content = archive.read(info)
            if hashlib.sha256(content).hexdigest() != expected:
                raise ValueError(f"更新檔案雜湊不符：{name}")
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        (target / "PACKAGE.json").write_bytes(manifest_data)
    from check_update import validate
    validate(target)
    return meta


def local_manifest(root: Path) -> dict | None:
    try:
        meta = json.loads((root / "PACKAGE.json").read_text(encoding="utf-8"))
        if not isinstance(meta, dict) or not isinstance(meta.get("files"), dict):
            return None
        for name in meta["files"]:
            safe_name(name)
        return meta
    except (OSError, ValueError, TypeError, IndexError):
        return None


def apply_staged(root: Path, staged: Path, new_meta: dict):
    if (root / ".aigo").exists() or (root / ".env").exists():
        raise ValueError("技能目錄含工作區或憑證，請移至技能目錄外；本次不更新")
    old = local_manifest(root)
    names = set(new_meta["files"]) | set((old or {}).get("files", {})) | {"PACKAGE.json"}
    for name in names - {"PACKAGE.json"}:
        safe_name(name)
    backup = {}
    for name in names:
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("安裝路徑含不安全連結")
        # Refuse directory/file transitions before the first mutation. Empty or
        # unknown directories belong to the user; never remove them implicitly.
        if path.exists() and not path.is_file():
            raise ValueError("更新檔案與既有資料夾撞名；本次未更新，請助教協助重新安裝")
        for parent in path.parents:
            if parent == root:
                break
            if parent.exists() and not parent.is_dir():
                raise ValueError("更新資料夾與既有檔案撞名；本次未更新，請助教協助重新安裝")
        backup[name] = path.read_bytes() if path.is_file() else None
    changed = []
    try:
        for name in sorted(names - {"PACKAGE.json"}):
            path = root / name
            if name in new_meta["files"]:
                atomic_write(path, (staged / name).read_bytes())
            else:
                path.unlink(missing_ok=True)
            changed.append(name)
        atomic_write(root / "PACKAGE.json", (staged / "PACKAGE.json").read_bytes())
        changed.append("PACKAGE.json")
        from check_update import validate
        validate(root)
    except Exception:
        for name in reversed(changed):
            value = backup[name]
            path = root / name
            if value is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, value)
        raise


def update(root: Path, *, now: float | None = None, state_file: Path | None = None) -> dict:
    root = root.resolve()
    if development_copy(root):
        return {"status": "development-copy", "updated": False}
    if (root / ".aigo").exists() or (root / ".env").exists():
        raise ValueError("技能目錄含工作區或憑證；請先移至技能目錄外")
    now = time.time() if now is None else now
    path = state_file or state_path(root)
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            state = {}
    except (OSError, ValueError):
        state = {}
    last_check = state.get("last_check", -INTERVAL)
    if isinstance(last_check, bool) or not isinstance(last_check, (float, int)) or not -INTERVAL <= last_check <= now:
        last_check = -INTERVAL
    if 0 <= now - last_check < INTERVAL:
        return {"status": "throttled", "updated": False, "next_check_seconds": int(INTERVAL - (now - last_check))}
    # Throttle failed checks too; no repeated network storm when offline.
    save_state(path, {**state, "last_check": now})
    commit = json.loads(fetch(f"https://api.github.com/repos/{REPOSITORY}/commits/main"))["sha"]
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("GitHub commit 回應無效")
    if commit == state.get("installed_commit"):
        from check_update import validate
        try:
            local = validate(root)
            return {"status": "current", "updated": False, "commit": commit, "version": local["version"]}
        except (OSError, ValueError, KeyError):
            pass  # Repair damaged install from the verified commit, even without a version bump.
    archive = fetch(f"https://codeload.github.com/{REPOSITORY}/zip/{commit}")
    with tempfile.TemporaryDirectory(prefix="aigo-learning-update-") as temp:
        staged = Path(temp)
        meta = stage_archive(archive, staged)
        local_meta = local_manifest(root)
        try:
            from check_update import validate
            validate(root)
            intact = True
        except (OSError, ValueError, KeyError):
            intact = False
        changed = meta != local_meta or not intact
        if changed:
            apply_staged(root, staged, meta)
    save_state(path, {"last_check": now, "installed_commit": commit, "version": meta["version"]})
    return {"status": "updated" if changed else "current", "updated": changed, "commit": commit, "version": meta["version"]}


def run_update(root: Path) -> int:
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    # OS file locks are released by the process, including crashes; no stale PID lease.
    with path.with_suffix(".lock").open("a+b") as lock:
        try:
            if os.name == "nt":
                import msvcrt
                if lock.tell() == 0:
                    lock.write(b"0")
                    lock.flush()
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            print(json.dumps({"status": "busy", "updated": False}))
            return 0
        try:
            result = update(root)
            print(json.dumps(result, ensure_ascii=False))
            return 0
        except Exception as exc:
            # Preserve old install, do not leak network response bodies or credentials.
            detail = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            try:
                from check_update import validate
                validate(root)
                intact = True
            except Exception:
                intact = False
            print(json.dumps({"status": "check-failed", "updated": False, "kept_current_install": intact, "error": detail}, ensure_ascii=False))
            return 1
