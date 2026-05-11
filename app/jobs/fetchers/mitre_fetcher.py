import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
from typing import Dict, Optional, Any
from urllib.parse import urljoin

from .base_fetcher import BaseFetcher

logger = logging.getLogger(__name__)

class MitreFetcher(BaseFetcher):
    """
    Fetcher para a API oficial do CVE Services (MITRE).
    Fonte: https://cveawg.mitre.org/api-docs/
    """
    
    BASE_URL = "https://cveawg.mitre.org/api/"
    
    def __init__(self, timeout: int = 30):
        super().__init__(timeout, user_agent='SOC360/1.0 (Internal Tool)')
        # Additional headers if needed
        self.session.headers.update({
            'Accept': 'application/json'
        })

    def fetch_cve(self, cve_id: str) -> Optional[Dict[str, Any]]:
        """
        Buscar um CVE específico na API da MITRE.
        """
        endpoint = f"cve/{cve_id}"
        return self._make_request(endpoint)

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """Executar requisição HTTP com tratamento de erros."""
        url = urljoin(self.BASE_URL, endpoint)
        
        try:
            logger.debug(f"Fetching MITRE URL: {url}")
            response = self.session.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"CVE not found in MITRE: {endpoint}")
                return None
            else:
                logger.error(f"MITRE API Error {response.status_code}: {response.text}")
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
