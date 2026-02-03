
import logging
import requests
import time
from typing import Dict, Optional, Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class MitreFetcher:
    """
    Fetcher para a API oficial do CVE Services (MITRE).
    Fonte: https://cveawg.mitre.org/api-docs/
    """
    
    BASE_URL = "https://cveawg.mitre.org/api/"
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Open-Monitor/1.0 (Internal Tool)',
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
            elif response.status_code == 429:
                logger.warning("Rate limit hit, waiting 5s...")
                time.sleep(5)
                return self._make_request(endpoint, params)
            else:
                logger.error(f"MITRE API Error {response.status_code}: {response.text}")
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
