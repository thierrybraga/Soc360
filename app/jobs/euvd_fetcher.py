
import logging
import requests
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class EUVDFetcher:
    """
    Fetcher para a API da European Vulnerability Database (EUVD).
    Fonte: https://euvd.enisa.europa.eu/apidoc
    """
    
    BASE_URL = "https://euvdservices.enisa.europa.eu/api/"
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Open-Monitor/1.0 (Internal Tool)',
            'Accept': 'application/json'
        })

    def fetch_search(
        self,
        page: int = 0,
        size: int = 100,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Buscar vulnerabilidades usando o endpoint de busca.
        
        Args:
            page: Número da página (0-indexado)
            size: Tamanho da página (max 100)
            from_date: Data inicial (YYYY-MM-DD)
            to_date: Data final (YYYY-MM-DD)
            **kwargs: Outros filtros (vendor, product, etc)
        """
        endpoint = "search"
        params = {
            "page": page,
            "size": size,
            **kwargs
        }
        
        if from_date:
            params["fromDate"] = from_date
        if to_date:
            params["toDate"] = to_date
            
        return self._make_request(endpoint, params)

    def fetch_latest(self) -> List[Dict[str, Any]]:
        """Buscar as últimas vulnerabilidades registradas."""
        return self._make_request("lastvulnerabilities")

    def fetch_critical(self) -> List[Dict[str, Any]]:
        """Buscar vulnerabilidades críticas recentes."""
        return self._make_request("criticalvulnerabilities")

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """Executar requisição HTTP com tratamento de erros."""
        url = urljoin(self.BASE_URL, endpoint)
        
        try:
            logger.debug(f"Fetching EUVD URL: {url} Params: {params}")
            response = self.session.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # Rate limit handling (simple retry)
                logger.warning("Rate limit hit, waiting 5s...")
                time.sleep(5)
                return self._make_request(endpoint, params)
            else:
                logger.error(f"EUVD API Error {response.status_code}: {response.text}")
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise

