"""
QQAQC GAN 적대적 결함 검증 단위 테스트 스위트
RED TEAM(최진혁)이 지속 고도화한 13대 적대적 결함 시나리오에 대한 시스템의
100% 방어력과 0 False Positive를 검증합니다.
"""
from src.qaqc.gan_discriminator import GanDiscriminator
from src.qaqc.qqaqc_runner import run_qqaqc_adversarial_audit


def test_gan_all_adversarial_scenarios_defended():
    """13대 적대적 시나리오가 모두 정상 방어(RED/YELLOW 또는 차단)되는지 검증."""
    discriminator = GanDiscriminator()
    report = discriminator.run_all()

    assert report["total_scenarios"] == 13
    assert report["false_positive_count"] == 0, f"False Positive 발견: {report['results']}"
    assert report["robustness_rate_pct"] == 100.0
    assert report["all_defended"] is True


def test_gan_new_boundary_attack_defended_after_blue_team_fix():
    """고도화된 경계값 부채비율(500%) 탈락 편취 공격이 Blue Team 결함 수정 후 정상 방어되는지 검증."""
    discriminator = GanDiscriminator()
    report = discriminator.run_all()

    boundary = [s for s in report["results"] if s["scenario_id"] == "ADV-11-DEBT-RATIO-BOUNDARY-INCLUSIVE"]
    assert len(boundary) == 1
    assert boundary[0]["defended"] is True
    assert boundary[0]["verdict"] == "RED"


def test_gan_member_5ball_over_limit_attack_defended():
    """참여연구원 5공 동시 수행 한도 초과 공격이 정상 방어되는지 검증."""
    discriminator = GanDiscriminator()
    report = discriminator.run_all()

    over = [s for s in report["results"] if s["scenario_id"] == "ADV-12-5BALL-OVER-MEMBER-MINOR"]
    assert len(over) == 1
    assert over[0]["defended"] is True
    assert over[0]["verdict"] == "RED"


def test_gan_safe_degrade_attack_defended():
    """비정상 입력 타입 크래시 공격에 대한 Safe Degrade RED 처리가 정상 동작하는지 검증."""
    discriminator = GanDiscriminator()
    report = discriminator.run_all()

    degrade = [s for s in report["results"] if s["scenario_id"] == "ADV-13-SAFER-DEGRADE-UNNORMAL-INPUT"]
    assert len(degrade) == 1
    assert degrade[0]["defended"] is True
    assert degrade[0]["verdict"] == "RED"


def test_qqaqc_runner_and_report_generation(tmp_path):
    """QQAQC 러너 실행 및 감사 리포트 JSON/MD 영속화 검증."""
    report = run_qqaqc_adversarial_audit(output_dir=str(tmp_path))

    assert report["gate_status"] == "APPROVED (Zero-Defect Deploy Ready)"
    assert (tmp_path / "qqaqc_adversarial_report.json").exists()
    assert (tmp_path / "qqaqc_adversarial_report.md").exists()
    assert len(report["expert_board"]) == 4
