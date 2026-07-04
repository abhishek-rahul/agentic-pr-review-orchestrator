import os

from app.schemas.rag import RepoFile

ALLOWED_EXTENSIONS = {".py", ".md", ".txt", ".toml", ".yaml", ".yml", ".json"}
SKIP_FOLDERS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", "dist", "build"}
SKIP_FILE_NAMES = {".env"}
SKIP_EXTENSIONS = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".zip"}


def load_repo_files(repo_path: str) -> list[RepoFile]:
    if not os.path.isdir(repo_path):
        raise ValueError(f"Repo path must be an existing directory: {repo_path}")

    repo_files: list[RepoFile] = []

    for current_dir, dir_names, file_names in os.walk(repo_path):
        dir_names[:] = [name for name in dir_names if name not in SKIP_FOLDERS]

        for file_name in file_names:
            full_path = os.path.join(current_dir, file_name)
            if not _should_load_file(file_name):
                continue

            content = _read_text_file(full_path)
            if content is None:
                continue

            relative_path = os.path.relpath(full_path, repo_path).replace(os.sep, "/")
            repo_files.append(RepoFile(file_path=relative_path, content=content))

    return repo_files


def _should_load_file(file_name: str) -> bool:
    lower_name = file_name.lower()
    _, extension = os.path.splitext(lower_name)

    if lower_name in SKIP_FILE_NAMES:
        return False
    if extension in SKIP_EXTENSIONS:
        return False
    return extension in ALLOWED_EXTENSIONS


def _read_text_file(file_path: str) -> str | None:
    try:
        raw_content = open(file_path, "rb").read()
    except OSError:
        return None

    if b"\0" in raw_content:
        return None

    try:
        return raw_content.decode("utf-8")
    except UnicodeDecodeError:
        return None
