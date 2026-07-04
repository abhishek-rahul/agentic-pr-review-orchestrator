from app.schemas.rag import RepoChunk, RepoFile


def split_repo_file(
    repo_file: RepoFile,
    chunk_size: int = 1200,
    overlap: int = 150,
) -> list[RepoChunk]:
    _validate_split_settings(chunk_size, overlap)

    if not repo_file.content.strip():
        return []

    chunks: list[RepoChunk] = []
    step_size = chunk_size - overlap

    for start in range(0, len(repo_file.content), step_size):
        chunk_content = repo_file.content[start : start + chunk_size]
        if not chunk_content.strip():
            continue

        chunk_index = len(chunks)
        chunks.append(
            RepoChunk(
                file_path=repo_file.file_path,
                chunk_id=f"{repo_file.file_path}:{chunk_index}",
                chunk_index=chunk_index,
                content=chunk_content,
            )
        )

        if start + chunk_size >= len(repo_file.content):
            break

    return chunks


def _validate_split_settings(chunk_size: int, overlap: int) -> None:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0:
        raise ValueError("overlap must be greater than or equal to 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
