"""Deterministic repository analysis-scope decisions and reporting."""

from pathlib import Path
import re


ILLUSTRATIVE_DIRECTORIES = (
    "examples", "samples", "fixtures", "testdata", "demos", "scaffolding", "demo", "scaffold",
)
FILE_HINT = "file"
DECLARATION_HINT = "declaration"
_HINT_RE = re.compile(r"\bpanopticon-ignore\s+(file|declaration)\b")


def path_reason(relative_path):
    """Return the illustrative-directory reason for ``relative_path``, or ``None``."""
    for part in Path(relative_path).parts[:-1]:
        if part.lower() in ILLUSTRATIVE_DIRECTORIES:
            return f"illustrative directory: {part}"
    return None


def file_reason(relative_path, text):
    """Return the exclusion reason for a path/file pair, or ``None``."""
    reason = path_reason(relative_path)
    if reason:
        return reason
    nonblank_lines = (line for line in text.splitlines() if line.strip())
    for line in tuple(nonblank_lines)[:5]:
        match = _HINT_RE.search(line)
        if match and match.group(1) == FILE_HINT:
            return "explicit file hint"
    return None


def declaration_reason(text, line_number):
    """Return the declaration-hint reason for a one-based declaration line, or ``None``."""
    lines = text.splitlines()
    for index in (line_number - 1, line_number - 2):
        if 0 <= index < len(lines):
            match = _HINT_RE.search(lines[index])
            if match and match.group(1) == DECLARATION_HINT:
                return "explicit declaration hint"
    return None


def filter_candidates(candidates, texts):
    """Return candidates not marked by declaration hints and their exclusion reports."""
    kept, reports = [], []
    for candidate in candidates:
        line_number = candidate.get("source_line")
        reason = (
            declaration_reason(texts[candidate["source_file"]], line_number)
            if line_number and candidate["source_file"] in texts else None
        )
        if reason:
            reports.append(f"excluded {candidate['source_file']}:{line_number} ({reason})")
        else:
            kept.append(candidate)
    return kept, reports


def redact_ignored_declarations(text):
    """Remove declaration hints and their annotated lines before LLM prompt construction."""
    lines = text.splitlines(keepends=True)
    ignored = set()
    for index, line in enumerate(lines):
        match = _HINT_RE.search(line)
        if not match or match.group(1) != DECLARATION_HINT:
            continue
        ignored.add(index)
        content = line[1:] if line.startswith(("+", "-")) else line
        if content.strip().startswith(("#", "//", "--")) and index + 1 < len(lines):
            ignored.add(index + 1)
    return "".join(line for index, line in enumerate(lines) if index not in ignored)


def excluded_directories(repo_root):
    """Return sorted repository-relative illustrative directories actually present."""
    root = Path(repo_root)
    paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_dir() and path.name.lower() in ILLUSTRATIVE_DIRECTORIES
    }
    return tuple(sorted(paths))


def exclusion_reports(repo_root):
    """Return stable reports for every excluded file in a repository."""
    root = Path(repo_root)
    reports = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        reason = file_reason(relative, text)
        if reason:
            reports.append(f"excluded {relative} ({reason})")
    return reports
