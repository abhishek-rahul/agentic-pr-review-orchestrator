import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def main() -> None:
    from app.rag.repo_index_service import index_local_repo

    parser = argparse.ArgumentParser(description="Index a local repo into Elasticsearch.")
    parser.add_argument("--repo-path", required=True)
    parser.add_argument("--repo-name", required=True)
    parser.add_argument("--branch", default="main")
    args = parser.parse_args()

    count = index_local_repo(args.repo_path, args.repo_name, args.branch)
    print(f"Indexed {count} chunks for repo {args.repo_name} on branch {args.branch}")


if __name__ == "__main__":
    main()
