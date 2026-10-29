#!/usr/bin/env python3
"""
scripts/generate_core_value_video.py
과제비서 AI 기본 플랫폼 순기능(탐색 피로 해소, 자동 수집, 자격 사전 진단, 맞춤 매칭, D-day 일정 관제)
시네마틱 영상물 자동 생성 엔진 (Pillow + FFmpeg 파이프라인)
"""
import os
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEDIA_DIR = PROJECT_ROOT / "src" / "web" / "static" / "media" / "intro"
OUTPUT_MP4 = MEDIA_DIR / "intro_showreel.mp4"
OUTPUT_STANDALONE = MEDIA_DIR / "core_value_showreel_2026.mp4"

WIDTH = 1280
HEIGHT = 720
FPS = 30

FONT_PATH = "/System/Library/Fonts/AppleSDGothicNeo.ttc"


def get_font(size: int, bold: bool = False):
    try:
        index = 2 if bold else 0  # 2: Bold, 0: Regular
        return ImageFont.truetype(FONT_PATH, size, index=index)
    except Exception:
        return ImageFont.load_default()


SCENES = [
    {
        "image": "story_act1_exhaustion.jpg",
        "duration": 4.0,
        "zoom_dir": "in",
        "badge": "탐색의 피로 해소",
        "badge_color": (239, 68, 68),  # Rose
        "title": "수십 개 사이트, 100페이지 공고문...",
        "subtitle": "매일 밤새워 헤매다 뒤늦게 결격 확인하는 피로를 끝냅니다.",
    },
    {
        "image": "step1_107_portals_radar.jpg",
        "duration": 4.0,
        "zoom_dir": "pan_right",
        "badge": "순기능 1: 전국 공고 매일 자동 수집",
        "badge_color": (14, 165, 233),  # Cyan
        "title": "나라장터 · K-Startup · 국가 R&D 포털 통합",
        "subtitle": "전국 공고를 매일 자동으로 수집하여 단일 창구에 정리합니다.",
    },
    {
        "image": "step2_copilot_morphing.jpg",
        "duration": 4.0,
        "zoom_dir": "in",
        "badge": "순기능 2: 25대 결격사유 1초 사전 진단",
        "badge_color": (16, 185, 129),  # Emerald
        "title": "기업 프로필 기반 자격 요건 정밀 분석",
        "subtitle": "업력·지역·업종 결격 사유를 사전에 걸러내어 헛걸음을 차단합니다.",
    },
    {
        "image": "story_act3_warm_guide.jpg",
        "duration": 4.0,
        "zoom_dir": "pan_left",
        "badge": "순기능 3: 기업 맞춤형 적합도 매칭",
        "badge_color": (168, 85, 247),  # Purple
        "title": "수천 개 공고 중 내 기업에 꼭 맞는 지원사업 선별",
        "subtitle": "RFP 핵심 과업과 기업 보유 역량을 0% 허위 없이 정밀 매칭합니다.",
    },
    {
        "image": "story_act4_winning_joy.jpg",
        "duration": 4.0,
        "zoom_dir": "out",
        "badge": "순기능 4: D-day 일정 관제 & 적시 지원",
        "badge_color": (245, 158, 11),  # Amber
        "title": "놓치지 않는 마감일, 완성도 높은 준비",
        "subtitle": "공고 탐색은 비서에게 맡기고, 대표님은 본업에만 집중하십시오.",
    },
    {
        "image": "hero_fatigue_vs_winning_edge.jpg",
        "duration": 4.0,
        "zoom_dir": "in",
        "badge": "대한민국 창업가를 위한 과제비서",
        "badge_color": (6, 182, 212),  # Cyan
        "title": "모두의 창업 과제비서 AI",
        "subtitle": "정부지원사업 맞춤형 공고 매칭 & 지원 자격 진단",
    },
]


def render_scene_frame(
    base_img: Image.Image,
    scene: dict,
    progress: float,
    font_badge,
    font_title,
    font_sub,
) -> Image.Image:
    # 1. Ken Burns Effect (Zoom or Pan)
    orig_w, orig_h = base_img.size
    zoom_dir = scene.get("zoom_dir", "in")

    if zoom_dir == "in":
        scale = 1.0 + 0.12 * progress
        cx, cy = orig_w / 2, orig_h / 2
    elif zoom_dir == "out":
        scale = 1.12 - 0.12 * progress
        cx, cy = orig_w / 2, orig_h / 2
    elif zoom_dir == "pan_right":
        scale = 1.08
        cx = orig_w * (0.45 + 0.10 * progress)
        cy = orig_h / 2
    else:  # pan_left
        scale = 1.08
        cx = orig_w * (0.55 - 0.10 * progress)
        cy = orig_h / 2

    crop_w = orig_w / scale
    crop_h = orig_h / scale
    left = max(0, cx - crop_w / 2)
    top = max(0, cy - crop_h / 2)
    right = min(orig_w, left + crop_w)
    bottom = min(orig_h, top + crop_h)

    frame = base_img.crop((left, top, right, bottom))
    frame = frame.resize((WIDTH, HEIGHT), Image.Resampling.BILINEAR)

    # 2. Cinematic Gradients Overlay (Top & Bottom Vignette)
    gradient = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(gradient)

    # Top subtle dark gradient
    for y in range(120):
        alpha = int(140 * (1.0 - y / 120))
        g_draw.line([(0, y), (WIDTH, y)], fill=(15, 23, 42, alpha))

    # Bottom deep cinematic gradient for text legibility
    for y in range(HEIGHT - 280, HEIGHT):
        p = (y - (HEIGHT - 280)) / 280
        alpha = int(220 * (p ** 1.3))
        g_draw.line([(0, y), (WIDTH, y)], fill=(10, 15, 30, alpha))

    frame = Image.alpha_composite(frame.convert("RGBA"), gradient)
    draw = ImageDraw.Draw(frame)

    # 3. Draw Badge (Rounded Box)
    badge_text = scene["badge"]
    badge_bbox = font_badge.getbbox(badge_text)
    bw = badge_bbox[2] - badge_bbox[0] + 24
    bh = badge_bbox[3] - badge_bbox[1] + 12
    bx = 60
    by = HEIGHT - 220

    badge_col = scene.get("badge_color", (6, 182, 212))
    # Semi-transparent badge background
    draw.rounded_rectangle(
        [bx, by, bx + bw, by + bh],
        radius=6,
        fill=(badge_col[0], badge_col[1], badge_col[2], 220),
    )
    draw.text((bx + 12, by + 4), badge_text, font=font_badge, fill=(255, 255, 255, 255))

    # 4. Draw Title
    title_text = scene["title"]
    tx = 60
    ty = by + bh + 14
    # Drop shadow
    draw.text((tx + 2, ty + 2), title_text, font=font_title, fill=(0, 0, 0, 200))
    draw.text((tx, ty), title_text, font=font_title, fill=(255, 255, 255, 255))

    # 5. Draw Subtitle
    sub_text = scene["subtitle"]
    sx = 60
    sy = ty + 46
    draw.text((sx + 1, sy + 1), sub_text, font=font_sub, fill=(0, 0, 0, 180))
    draw.text((sx, sy), sub_text, font=font_sub, fill=(226, 232, 240, 255))

    # 6. Top Bar Branding
    brand_text = "과제비서 AI  |  정부지원사업 공고 매칭 & 자격 진단"
    draw.text((62, 32), brand_text, font=font_sub, fill=(0, 0, 0, 160))
    draw.text((60, 30), brand_text, font=font_sub, fill=(148, 163, 184, 255))

    return frame.convert("RGB")


def main():
    print("🎬 과제비서 AI 순기능 시네마틱 영상물 생성 시작...")
    font_badge = get_font(18, bold=True)
    font_title = get_font(34, bold=True)
    font_sub = get_font(20, bold=False)

    total_duration = sum(s["duration"] for s in SCENES)
    total_frames = int(total_duration * FPS)
    print(f"총 {len(SCENES)}개 씬, 러닝타임: {total_duration:.1f}초, 프레임 수: {total_frames}장")

    # FFmpeg Pipe 시작
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-",  # Video input from stdin
        # Background ambient sound synthesis (soothing tech pad)
        "-f", "lavfi",
        "-i", f"sine=frequency=220:duration={total_duration},volume=0.08",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "21",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        str(OUTPUT_MP4),
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    try:
        current_frame = 0
        for s_idx, scene in enumerate(SCENES, 1):
            img_path = MEDIA_DIR / scene["image"]
            if not img_path.exists():
                print(f"경고: 이미지 {img_path} 부재, 기본 검정 배경 사용")
                base_img = Image.new("RGB", (WIDTH, HEIGHT), (15, 23, 42))
            else:
                base_img = Image.open(img_path).convert("RGB")

            scene_frames = int(scene["duration"] * FPS)
            print(f"▶ 씬 {s_idx}/{len(SCENES)} 렌더링 중: {scene['badge']} ({scene_frames} 프레임)...")

            for f in range(scene_frames):
                progress = f / max(1, scene_frames - 1)
                frame = render_scene_frame(
                    base_img, scene, progress, font_badge, font_title, font_sub
                )
                proc.stdin.write(frame.tobytes())
                current_frame += 1

        proc.stdin.close()
        proc.wait()

        if proc.returncode == 0:
            print(f"✅ 영상 제작 성공: {OUTPUT_MP4}")
            # Standalone 복사본 저장
            import shutil
            shutil.copyfile(OUTPUT_MP4, OUTPUT_STANDALONE)
            print(f"✅ 백업 보관: {OUTPUT_STANDALONE}")
            size_mb = os.path.getsize(OUTPUT_MP4) / (1024 * 1024)
            print(f"📊 최종 파일 크기: {size_mb:.2f} MB, 해상도: {WIDTH}x{HEIGHT}, 30fps")
        else:
            print(f"❌ FFmpeg 실패 코드: {proc.returncode}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ 렌더링 오류 발생: {e}")
        if proc:
            proc.kill()
        sys.exit(1)


if __name__ == "__main__":
    main()
