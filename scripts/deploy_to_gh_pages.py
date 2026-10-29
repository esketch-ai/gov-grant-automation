#!/usr/bin/env python3
"""
Deploy static bundle directly to gh-pages branch on GitHub.

1. scripts/build_github_pages.py 를 실행하여 dist/ 폴더 생성
2. git 임시 인덱스를 사용하여 dist/ 의 내용만을 루트로 하는 커밋 생성
3. remote 'github'의 'gh-pages' 브랜치로 즉시 푸시
"""

import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run(cmd: str, check: bool = True) -> str:
    print(f"  $ {cmd}")
    res = subprocess.run(cmd, shell=True, cwd=REPO_ROOT, capture_output=True, text=True)
    if check and res.returncode != 0:
        print(f"❌ Error (code {res.returncode}):\n{res.stderr}")
        sys.exit(res.returncode)
    return res.stdout.strip()


def main():
    print("🚀 [모두의 창업비서 SSA] GitHub Pages 직접 배포 시작...")

    # 1. 정적 빌드 수행
    print("\n[Step 1] 정적 사이트 빌드 (scripts/build_github_pages.py)")
    run(f"{sys.executable} scripts/build_github_pages.py --out-dir dist")

    # 2. 임시 Git 인덱스를 이용해 dist 디렉토리를 루트로 하는 트리 생성
    print("\n[Step 2] dist/ 디렉토리 트리 객체 생성")
    env = dict(**subprocess.os.environ)
    env["GIT_INDEX_FILE"] = str(REPO_ROOT / ".git" / "temp_gh_pages_index")

    # 기존 임시 인덱스 정리
    temp_index = REPO_ROOT / ".git" / "temp_gh_pages_index"
    if temp_index.exists():
        temp_index.unlink()

    # dist 파일들을 임시 인덱스에 추가
    res = subprocess.run(
        "git --work-tree=dist add -A .",
        shell=True,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        print(f"❌ Failed to stage dist: {res.stderr}")
        sys.exit(1)

    # 트리 객체 작성
    res = subprocess.run(
        "git write-tree",
        shell=True,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        print(f"❌ Failed to write tree: {res.stderr}")
        sys.exit(1)
    tree_id = res.stdout.strip()
    print(f"  ✅ 생성된 Tree ID: {tree_id}")

    # 커밋 객체 생성
    commit_msg = "Deploy 모두의 창업비서 (SSA) to GitHub Pages [skip ci]"
    res = subprocess.run(
        f'git commit-tree {tree_id} -m "{commit_msg}"',
        shell=True,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        print(f"❌ Failed to create commit: {res.stderr}")
        sys.exit(1)
    commit_id = res.stdout.strip()
    print(f"  ✅ 생성된 Commit ID: {commit_id}")

    # 임시 인덱스 삭제
    if temp_index.exists():
        temp_index.unlink()

    # 3. GitHub remote의 gh-pages 브랜치로 푸시
    print("\n[Step 3] github/gh-pages 브랜치로 푸시")
    res = subprocess.run(
        f"git push github {commit_id}:refs/heads/gh-pages --force",
        shell=True,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        print(f"⚠️ Push 실패 또는 권한 필요:\n{res.stderr}")
        print("💡 수동으로 푸시하려면: git push github <commit_id>:refs/heads/gh-pages")
        return

    print(f"\n🎉 github/gh-pages 브랜치 배포 성공! ({commit_id})\n")


if __name__ == "__main__":
    main()
