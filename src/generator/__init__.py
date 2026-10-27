"""
과제별 사업계획서 맞춤 변환 및 작성 코파일럿 모듈
"""
from .template_schemas import ProposalTemplate, SectionRequirement, get_template, get_all_templates, detect_template_for_announcement
from .gap_analyzer import ProposalGapAnalyzer, SectionGapAnalysis
from .doc_morpher import DocMorpher

__all__ = [
    "ProposalTemplate",
    "SectionRequirement",
    "get_template",
    "get_all_templates",
    "detect_template_for_announcement",
    "ProposalGapAnalyzer",
    "SectionGapAnalysis",
    "DocMorpher",
]
