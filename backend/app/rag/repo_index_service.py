import os

from app.rag.file_loader import load_repo_files
from app.rag.indexer import index_repo_chunks
from app.rag.text_splitter import split_repo_file
from app.schemas.rag import RepoChunk

# ye coordinator type h 
def index_local_repo(repo_path: str, repo_name: str, branch: str = "main") -> int:
    if not os.path.isdir(repo_path):
        raise ValueError(f"Repo path must be an existing directory: {repo_path}")

    repo_files = load_repo_files(repo_path)
    chunks: list[RepoChunk] = []
    for repo_file in repo_files:
        chunks.extend(split_repo_file(repo_file))

    return index_repo_chunks(repo_name, branch, chunks)
