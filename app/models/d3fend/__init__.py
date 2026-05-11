"""
SOC360 D3FEND Models
Modelos para integração com MITRE D3FEND Framework
"""
from app.models.d3fend.d3fend_technique import D3fendTechnique
from app.models.d3fend.d3fend_artifact import D3fendArtifact
from app.models.d3fend.d3fend_tactic import D3fendTactic
from app.models.d3fend.d3fend_offensive_mapping import D3fendOffensiveMapping
from app.models.d3fend.cve_d3fend_correlation import CveD3fendCorrelation

__all__ = [
    'D3fendTechnique',
    'D3fendArtifact', 
    'D3fendTactic',
    'D3fendOffensiveMapping',
    'CveD3fendCorrelation'
]
