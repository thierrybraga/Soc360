"""
Fetcher para o framework MITRE ATT&CK via dados STIX 2.1.
Fonte: https://github.com/mitre-attack/attack-stix-data
"""
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, List, Optional, Any

from .base_fetcher import BaseFetcher

logger = logging.getLogger(__name__)

class MitreAttackFetcher(BaseFetcher):
    """
    Fetcher para o MITRE ATT&CK.
    Consome os arquivos JSON (STIX 2.1) oficiais do repositório attack-stix-data.
    """
    
    BASE_URL = "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/"
    
    DOMAINS = [
        "enterprise-attack",
        "mobile-attack",
        "ics-attack"
    ]
    
    def __init__(self, timeout: int = 60):
        super().__init__(timeout, user_agent='Open-Monitor/1.0 (Security Intelligence Tool)')
        # Additional headers if needed
        self.session.headers.update({
            'Accept': 'application/json'
        })

    def fetch_domain_data(self, domain: str = "enterprise-attack") -> Optional[Dict[str, Any]]:
        """
        Busca o bundle STIX completo de um domínio do ATT&CK.
        """
        if domain not in self.DOMAINS:
            logger.error(f"Invalid MITRE ATT&CK domain: {domain}")
            return None
            
        url = f"{self.BASE_URL}{domain}/{domain}.json"
        
        try:
            logger.info(f"Downloading MITRE ATT&CK data for domain: {domain}...")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to download MITRE ATT&CK data from {url}: {e}")
            return None

    def get_all_domains(self) -> Dict[str, Any]:
        """
        Busca dados de todos os domínios suportados.
        """
        results = {}
        for domain in self.DOMAINS:
            data = self.fetch_domain_data(domain)
            if data:
                results[domain] = data
        return results
