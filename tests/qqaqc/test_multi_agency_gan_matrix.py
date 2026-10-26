"""
QQAQC 8대 BM × 14대 기관 공고 (112쌍) GAN 매트릭스 단위 테스트
모든 기관별/BM별 정합률, 0 False Positive, 0 Crash 검증.
"""
from src.qaqc.gan_multi_agency_matrix import GanMultiAgencyMatrix
from src.qaqc.multi_agency_matrix_runner import run_multi_agency_matrix_audit


def test_multi_agency_gan_matrix_evaluation():
    """8대 BM × 14대 기관 공고 매칭 정밀도 및 0 False Positive 검증."""
    matrix = GanMultiAgencyMatrix()
    data = matrix.evaluate_all()

    assert data["total_pairs"] == 112
    # 치명적 오탐(부적격 과제를 GREEN으로 잘못 추천)은 0건이어야 함
    assert data["false_positive_count"] == 0, f"False Positive 발생: {[r for r in data['results'] if r.get('error_type') == 'FALSE_POSITIVE']}"
    # 종합 정합률 95% 이상
    assert data["accuracy_rate_pct"] >= 95.0
    # 평균 소요 시간 20ms 미만 (초고속 연산)
    assert data["avg_ms_per_pair"] < 20.0


def test_multi_agency_matrix_runner_generation(tmp_path):
    """다기관 매트릭스 감사 러너 실행 및 리포트 파일 생성 검증."""
    report = run_multi_agency_matrix_audit(output_dir=str(tmp_path))

    assert report["summary"]["total_pairs"] == 112
    assert report["summary"]["status"].startswith("APPROVED")
    assert (tmp_path / "qqaqc_multi_agency_matrix_report.json").exists()
    assert (tmp_path / "qqaqc_multi_agency_matrix_report.md").exists()
