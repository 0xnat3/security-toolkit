"""File integrity: hash a directory tree, then compare two snapshots. Pure logic."""
import hashlib
import os

ALGORITHMS = ("sha256", "sha512", "sha1", "md5")
DEFAULT_ALGORITHM = "sha256"
DEFAULT_EXCLUDES = frozenset({"venv", ".venv", "__pycache__", ".git", "node_modules", "instance"})
MAX_FILES = 50_000
CHUNK_SIZE = 64 * 1024


def validate_algorithm(algorithm: str | None) -> str:
    algorithm = (algorithm or DEFAULT_ALGORITHM).lower()
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    return algorithm


def hash_file(path: str, algorithm: str = DEFAULT_ALGORITHM) -> str:
    h = hashlib.new(validate_algorithm(algorithm))
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            h.update(chunk)
    return h.hexdigest()


def snapshot(directory: str, algorithm: str = DEFAULT_ALGORITHM, excludes=DEFAULT_EXCLUDES) -> dict:
    """Hash every file under `directory`. Paths are stored relative to it."""
    algorithm = validate_algorithm(algorithm)
    root = os.path.abspath(directory or ".")
    if not os.path.isdir(root):
        raise ValueError(f"Not a directory: {directory}")

    files: dict[str, str] = {}
    skipped: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in excludes]  # prune before descending
        for name in filenames:
            path = os.path.join(dirpath, name)
            if os.path.islink(path):
                continue
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            if len(files) >= MAX_FILES:
                raise ValueError(f"Too many files (limit {MAX_FILES}). Choose a smaller directory.")
            try:
                files[rel] = hash_file(path, algorithm)
            except OSError:
                skipped.append(rel)  # unreadable or locked: report it, don't hide it

    return {"root": root, "algorithm": algorithm, "files": files, "skipped": sorted(skipped)}


def compare(baseline: dict[str, str], current: dict[str, str]) -> dict:
    added = sorted(current.keys() - baseline.keys())
    removed = sorted(baseline.keys() - current.keys())
    modified = sorted(p for p in current.keys() & baseline.keys() if current[p] != baseline[p])
    return {
        "added": added,
        "removed": removed,
        "modified": modified,
        "summary": f"Added: {len(added)}, Removed: {len(removed)}, Modified: {len(modified)}",
    }