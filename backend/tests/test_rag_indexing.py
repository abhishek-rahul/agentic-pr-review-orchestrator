import pytest

from app.rag.file_loader import load_repo_files
from app.rag.text_splitter import split_repo_file
from app.schemas.rag import RepoFile


def test_loader_includes_valid_text_files(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "service.py").write_text("def run():\n    return True\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Sample repo\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
    (tmp_path / "config.yaml").write_text("debug: false\n", encoding="utf-8")

    files = load_repo_files(str(tmp_path))
    file_paths = {repo_file.file_path for repo_file in files}

    assert "app/service.py" in file_paths
    assert "README.md" in file_paths
    assert "pyproject.toml" in file_paths
    assert "config.yaml" in file_paths


def test_loader_skips_env_ignored_folders_and_nul_bytes(tmp_path):
    (tmp_path / ".env").write_text("OPENAI_API_KEY=secret\n", encoding="utf-8")
    (tmp_path / "safe.py").write_text("print('safe')\n", encoding="utf-8")
    (tmp_path / "binary.py").write_bytes(b"hello\0world")

    for folder_name in ["node_modules", ".git", ".venv", "__pycache__"]:
        folder = tmp_path / folder_name
        folder.mkdir()
        (folder / "ignored.py").write_text("print('ignored')\n", encoding="utf-8")

    files = load_repo_files(str(tmp_path))
    file_paths = {repo_file.file_path for repo_file in files}

    assert "safe.py" in file_paths
    assert ".env" not in file_paths
    assert "binary.py" not in file_paths
    assert "node_modules/ignored.py" not in file_paths
    assert ".git/ignored.py" not in file_paths
    assert ".venv/ignored.py" not in file_paths
    assert "__pycache__/ignored.py" not in file_paths


def test_splitter_creates_stable_chunk_ids_and_indexes():
    repo_file = RepoFile(file_path="app/service.py", content="abcdefghijklmnopqrstuvwxyz")

    chunks = split_repo_file(repo_file, chunk_size=10, overlap=3)

    assert [chunk.chunk_id for chunk in chunks] == [
        "app/service.py:0",
        "app/service.py:1",
        "app/service.py:2",
        "app/service.py:3",
    ]
    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2, 3]
    assert chunks[0].content == "abcdefghij"
    assert chunks[1].content == "hijklmnopq"


def test_splitter_creates_multiple_overlapping_chunks_for_large_text():
    repo_file = RepoFile(file_path="README.md", content="0123456789" * 20)

    chunks = split_repo_file(repo_file, chunk_size=50, overlap=10)

    assert len(chunks) > 1
    assert chunks[0].content[-10:] == chunks[1].content[:10]


@pytest.mark.parametrize("content", ["", "   \n\t"])
def test_splitter_returns_empty_for_empty_or_whitespace_content(content):
    repo_file = RepoFile(file_path="README.md", content=content)

    assert split_repo_file(repo_file) == []


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [
        (0, 0),
        (10, -1),
        (10, 10),
        (10, 11),
    ],
)
def test_splitter_validates_invalid_chunk_settings(chunk_size, overlap):
    repo_file = RepoFile(file_path="README.md", content="hello world")

    with pytest.raises(ValueError):
        split_repo_file(repo_file, chunk_size=chunk_size, overlap=overlap)
