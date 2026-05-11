"""
SOC360 NVD Types
Data structures for NVD API responses.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict


@dataclass
class NVDResponse:
    """Resposta da API do NVD."""
    vulnerabilities: List[Dict]
    results_per_page: int
    start_index: int
    total_results: int
    timestamp: datetime