#!/usr/bin/env python3
"""
GitHub Pages Static Site Generator (SSG) for 모두의 창업비서 (SSA : Startup Secretary for All).

FastAPI 애플리케이션의 모든 라우트(Jinja2 템플릿)를 사전 렌더링(Pre-render)하여
정적 HTML, CSS, JS, 미디어 파일로 구성된 GitHub Pages 배포용 번들을 생성합니다.
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
import re

# Add repo root to PYTHONPATH
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from starlette.testclient import TestClient
from src.web.app import app, _get_db


BASE_ROUTES_MAP = [
    # (FastAPI 라우트, 저장될 파일명)
    ("/intro", "index.html"),
    ("/intro", "intro.html"),
    ("/feedback-lounge", "feedback_lounge.html"),
    ("/pricing", "pricing.html"),
    ("/dashboard", "dashboard.html"),
    ("/dashboard/biz", "biz_dashboard.html"),
    ("/announcements", "announcements.html"),
    ("/items", "items.html"),
    ("/matches", "matches.html"),
    ("/projects", "projects.html"),
    ("/proposals/tailor", "tailor.html"),
    ("/vault", "vault.html"),
    ("/portals", "portals.html"),
    ("/governance/partner", "governance_partner.html"),
    ("/admin/platform", "admin_platform.html"),
    ("/admin/audit-logs", "audit_logs.html"),
    ("/audit", "audit.html"),
    ("/logs", "logs.html"),
]


def postprocess_html(html: str) -> str:
    """GitHub Pages 호스팅 환경에 맞게 절대 경로를 상대 경로로 변환하고 Mock API 스크립트를 주입."""
    
    # 1. 정적 에셋 경로 상대화 (/static/ -> ./static/)
    html = re.sub(r'(href|src|poster)=["\']/static/([^"\']+)["\']', r'\1="./static/\2"', html)
    html = re.sub(r'url\(["\']?/static/([^)"\']+)["\']?\)', r'url("./static/\1")', html)

    # 2. 내부 라우트 링크 상대화
    replacements = [
        (r'href=["\']/feedback-lounge["\']', 'href="./feedback_lounge.html"'),
        (r'href=["\']/prototypes["\']', 'href="./feedback_lounge.html"'),
        (r'href=["\']/pricing["\']', 'href="./pricing.html"'),
        (r'href=["\']/dashboard/biz["\']', 'href="./biz_dashboard.html"'),
        (r'href=["\']/biz/dashboard["\']', 'href="./biz_dashboard.html"'),
        (r'href=["\']/dashboard["\']', 'href="./dashboard.html"'),
        (r'href=["\']/announcements["\']', 'href="./announcements.html"'),
        (r'href=["\']/items["\']', 'href="./items.html"'),
        (r'href=["\']/matches["\']', 'href="./matches.html"'),
        (r'href=["\']/projects["\']', 'href="./projects.html"'),
        (r'href=["\']/proposals/tailor["\']', 'href="./tailor.html"'),
        (r'href=["\']/vault["\']', 'href="./vault.html"'),
        (r'href=["\']/portals["\']', 'href="./portals.html"'),
        (r'href=["\']/governance/partner["\']', 'href="./governance_partner.html"'),
        (r'href=["\']/admin/platform["\']', 'href="./admin_platform.html"'),
        (r'href=["\']/admin/audit-logs["\']', 'href="./audit_logs.html"'),
        (r'href=["\']/audit["\']', 'href="./audit.html"'),
        (r'href=["\']/logs["\']', 'href="./logs.html"'),
        (r'href=["\']/intro["\']', 'href="./intro.html"'),
        (r'href=["\']/["\']', 'href="./index.html"'),
        # 일반 보고서 템플릿 패턴
        (r'href=["\']/prototype/report/([^"\']+)["\']', r'href="./prototype_report_\1.html"'),
        # JS 이벤트 핸들러 내부 경로 상대화
        (r"switchServiceRole\((['\"][^'\"]+['\"]),\s*['\"]/intro['\"]\)", r"switchServiceRole(\1, './intro.html')"),
        (r"switchServiceRole\((['\"][^'\"]+['\"]),\s*['\"]/dashboard/biz['\"]\)", r"switchServiceRole(\1, './biz_dashboard.html')"),
        (r"switchServiceRole\((['\"][^'\"]+['\"]),\s*['\"]/admin/platform['\"]\)", r"switchServiceRole(\1, './admin_platform.html')"),
        (r"location\.href=['\"]/feedback-lounge([^'\"]*)['\"]", r"location.href='./feedback_lounge.html\1'"),
    ]

    for pattern, repl in replacements:
        html = re.sub(pattern, repl, html)

    # 3. GitHub Pages Mock API 스크립트 주입 (닫는 </body> 태그 직전)
    mock_script_tag = """
  <!-- GitHub Pages Client-side Mock API Layer -->
  <script src="./static/js/github_pages_mock_api.js"></script>
</body>"""
    if "</body>" in html:
        html = html.replace("</body>", mock_script_tag)

    return html


def create_404_page() -> str:
    """GitHub Pages용 404 에러 페이지 (자동 홈 리다이렉트 및 내비게이션 포함)."""
    return """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>페이지를 찾을 수 없습니다 · 모두의 창업비서 (SSA)</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
  <link rel="stylesheet" href="./static/css/k_horizon_2027.css">
</head>
<body class="bg-slate-950 text-white min-h-screen flex items-center justify-center p-4">
  <div class="max-w-md w-full bg-slate-900 border border-white/10 rounded-2xl p-8 text-center shadow-2xl space-y-6">
    <div class="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center text-white shadow-lg">
      <i class="fa-solid fa-file-shield text-3xl"></i>
    </div>
    <div class="space-y-2">
      <h1 class="text-2xl font-black tracking-tight">모두의 창업비서 (SSA)</h1>
      <p class="text-xs text-cyan-300 font-bold uppercase tracking-wider">Startup Secretary for All</p>
    </div>
    <p class="text-sm text-slate-300 leading-relaxed">
      요청하신 페이지가 이동되었거나 존재하지 않습니다.<br>
      아래 메인 화면으로 이동해 주세요.
    </p>
    <div class="pt-2 flex flex-col gap-2.5">
      <a href="./index.html" class="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-bold text-sm shadow transition">
        <i class="fa-solid fa-house mr-1.5"></i> 인트로 메인으로 이동
      </a>
      <a href="./feedback_lounge.html" class="w-full py-2.5 px-4 rounded-xl bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs transition">
        <i class="fa-solid fa-comments mr-1.5"></i> 피드백 라운지 바로가기
      </a>
      <a href="./dashboard.html" class="w-full py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs transition">
        <i class="fa-solid fa-chart-line mr-1.5"></i> 관리 대시보드
      </a>
    </div>
  </div>
</body>
</html>
"""


def build_pages(out_dir: Path):
    """정적 사이트 빌드 실행."""
    print(f"🏗️  [모두의 창업비서 SSA] GitHub Pages 정적 빌드 시작: {out_dir}")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = TestClient(app)
    db = _get_db()
    db.ensure_schema()

    # 동적 캠페인 보고서 라우트 추가
    routes_to_render = list(BASE_ROUTES_MAP)
    all_campaigns = db.list_prototype_campaigns()
    for camp in all_campaigns[:6]:
        cid = camp["id"]
        routes_to_render.append((f"/prototype/report/{cid}", f"prototype_report_{cid}.html"))

    # 1. 템플릿 라우트 렌더링
    rendered_count = 0
    for route, filename in routes_to_render:
        print(f"  📄 렌더링 중: {route} -> {filename}")
        try:
            resp = client.get(route, headers={"Cookie": "user_role=visitor"})
            if resp.status_code == 200:
                processed_html = postprocess_html(resp.text)
                dest = out_dir / filename
                dest.write_text(processed_html, encoding="utf-8")
                rendered_count += 1
            else:
                print(f"    ⚠️ 경고: {route} 응답 코드 {resp.status_code}")
        except Exception as e:
            print(f"    ❌ 에러 발생 ({route}): {e}")

    # 2. 정적 에셋 복사 (src/web/static -> out_dir/static)
    src_static = REPO_ROOT / "src" / "web" / "static"
    dest_static = out_dir / "static"
    if src_static.exists():
        print(f"  📦 정적 에셋 복사: {src_static} -> {dest_static}")
        shutil.copytree(src_static, dest_static, dirs_exist_ok=True)

    # 3. 404.html 생성
    (out_dir / "404.html").write_text(create_404_page(), encoding="utf-8")
    print("  ✅ 404.html 생성 완료")

    # 4. .nojekyll 파일 생성 (GitHub Pages가 _static 등을 무시하지 않도록 함)
    (out_dir / ".nojekyll").touch()
    print("  ✅ .nojekyll 파일 생성 완료")

    print(f"\n🎉 GitHub Pages 정적 빌드 완료! 총 {rendered_count}개 페이지 렌더링 -> {out_dir}\n")


def main():
    parser = argparse.ArgumentParser(description="Build GitHub Pages static bundle")
    parser.add_argument("--out-dir", default="dist", help="Output directory for static site (default: dist)")
    args = parser.parse_args()

    out_path = Path(args.out_dir).resolve()
    build_pages(out_path)


if __name__ == "__main__":
    main()
