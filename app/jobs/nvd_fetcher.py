"""
Open-Monitor NVD Fetcher
Cliente HTTP para API do NVD com retry logic e rate limiting.
"""
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from flask import current_app


logger = logging.getLogger(__name__)


@dataclass
class NVDResponse:
    """Resposta da API do NVD."""
    vulnerabilities: List[Dict]
    results_per_page: int
    start_index: int
    total_results: int
    timestamp: datetime


class NVDFetcher:
    """
    Cliente HTTP para API NVD 2.0.
    
    Features:
    - Rate limiting automático (5 req/30s sem key, 50 req/30s com key)
    - Retry com exponential backoff
    - Suporte a API key
    - Janelas de tempo de 120 dias (limitação NVD)
    """
    
    BASE_URL = 'https://services.nvd.nist.gov/rest/json/cves/2.0'
    
    # Rate limits
    RATE_LIMIT_NO_KEY = 5  # req por 30 segundos
    RATE_LIMIT_WITH_KEY = 50  # req por 30 segundos
    RATE_WINDOW = 30  # segundos
    
    # Limites da API
    MAX_RESULTS_PER_PAGE = 2000
    MAX_DATE_RANGE_DAYS = 120
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializar fetcher.
        
        Args:
            api_key: API key do NVD (opcional, mas recomendado)
        """
        self.api_key = api_key or current_app.config.get('NVD_API_KEY')
        self.session = self._create_session()
        
        # Rate limiting state
        self._request_times: List[float] = []
        self._rate_limit = self.RATE_LIMIT_WITH_KEY if self.api_key else self.RATE_LIMIT_NO_KEY
        
        logger.info(
            f'NVDFetcher initialized (rate limit: {self._rate_limit} req/{self.RATE_WINDOW}s)'
        )
    
    def _create_session(self) -> requests.Session:
        """Criar sessão HTTP com retry."""
        session = requests.Session()
        
        # Retry strategy
        retry = Retry(
            total=5,
            backoff_factor=1,  # 1s, 2s, 4s, 8s, 16s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=['GET']
        )
        
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        
        # Headers
        session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'Open-Monitor/3.0 (Vulnerability Scanner)'
        })
        
        if self.api_key:
            session.headers['apiKey'] = self.api_key
        
        return session
    
    def _wait_for_rate_limit(self):
        """Aguardar se necessário para respeitar rate limit."""
        now = time.time()
        
        # Limpar timestamps antigos
        self._request_times = [
            t for t in self._request_times
            if now - t < self.RATE_WINDOW
        ]
        
        # Se atingiu limite, aguardar
        if len(self._request_times) >= self._rate_limit:
            oldest = min(self._request_times)
            sleep_time = self.RATE_WINDOW - (now - oldest) + 0.1
            
            if sleep_time > 0:
                logger.debug(f'Rate limit reached, sleeping {sleep_time:.1f}s')
                time.sleep(sleep_time)
        
        # Registrar request
        self._request_times.append(time.time())
    
    def fetch_page(
        self,
        start_index: int = 0,
        results_per_page: int = 2000,
        pub_start_date: Optional[datetime] = None,
        pub_end_date: Optional[datetime] = None,
        last_mod_start_date: Optional[datetime] = None,
        last_mod_end_date: Optional[datetime] = None,
        keyword_search: Optional[str] = None,
        cve_id: Optional[str] = None
    ) -> Optional[NVDResponse]:
        """
        Buscar uma página de CVEs da API.
        
        Args:
            start_index: Índice inicial (paginação)
            results_per_page: Resultados por página (max 2000)
            pub_start_date: Data inicial de publicação
            pub_end_date: Data final de publicação
            last_mod_start_date: Data inicial de modificação
            last_mod_end_date: Data final de modificação
            keyword_search: Busca por palavra-chave
            cve_id: CVE específico
            
        Returns:
            NVDResponse ou None se erro
        """
        # Rate limiting
        self._wait_for_rate_limit()
        
        # Construir parâmetros
        params = {
            'startIndex': start_index,
            'resultsPerPage': min(results_per_page, self.MAX_RESULTS_PER_PAGE)
        }
        
        # Filtros de data
        if pub_start_date:
            params['pubStartDate'] = pub_start_date.strftime('%Y-%m-%dT%H:%M:%S.000')
        if pub_end_date:
            params['pubEndDate'] = pub_end_date.strftime('%Y-%m-%dT%H:%M:%S.000')
        if last_mod_start_date:
            params['lastModStartDate'] = last_mod_start_date.strftime('%Y-%m-%dT%H:%M:%S.000')
        if last_mod_end_date:
            params['lastModEndDate'] = last_mod_end_date.strftime('%Y-%m-%dT%H:%M:%S.000')
        
        # Outros filtros
        if keyword_search:
            params['keywordSearch'] = keyword_search
        if cve_id:
            params['cveId'] = cve_id
        
        try:
            logger.debug(f'Fetching NVD API: startIndex={start_index}')
            
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            
            return NVDResponse(
                vulnerabilities=data.get('vulnerabilities', []),
                results_per_page=data.get('resultsPerPage', 0),
                start_index=data.get('startIndex', 0),
                total_results=data.get('totalResults', 0),
                timestamp=datetime.now(timezone.utc)
            )
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.error('NVD API: Access forbidden. Check API key.')
            elif e.response.status_code == 429:
                logger.warning('NVD API: Rate limit exceeded. Waiting...')
                time.sleep(30)
            else:
                logger.error(f'NVD API HTTP error: {e}')
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f'NVD API request error: {e}')
            return None
        
        except Exception as e:
            logger.error(f'NVD API unexpected error: {e}')
            return None
    
    def fetch_all_pages(
        self,
        pub_start_date: Optional[datetime] = None,
        pub_end_date: Optional[datetime] = None,
        last_mod_start_date: Optional[datetime] = None,
        last_mod_end_date: Optional[datetime] = None,
        progress_callback: Optional[callable] = None
    ) -> List[Dict]:
        """
        Buscar todas as páginas para um período.
        
        Args:
            pub_start_date: Data inicial de publicação
            pub_end_date: Data final de publicação
            last_mod_start_date: Data inicial de modificação
            last_mod_end_date: Data final de modificação
            progress_callback: Callback(current, total) para progresso
            
        Returns:
            Lista de todos os CVEs
        """
        all_vulnerabilities = []
        start_index = 0
        total_results = None
        
        while True:
            response = self.fetch_page(
                start_index=start_index,
                pub_start_date=pub_start_date,
                pub_end_date=pub_end_date,
                last_mod_start_date=last_mod_start_date,
                last_mod_end_date=last_mod_end_date
            )
            
            if response is None:
                if start_index == 0:
                    raise Exception("Failed to connect to NVD API. Check API Key and connectivity.")
                logger.error('Failed to fetch page, aborting')
                break
            
            if total_results is None:
                total_results = response.total_results
                logger.info(f'Total CVEs to fetch: {total_results}')
            
            all_vulnerabilities.extend(response.vulnerabilities)
            
            # Callback de progresso
            if progress_callback:
                progress_callback(len(all_vulnerabilities), total_results)
            
            # Verificar se terminou
            if start_index + response.results_per_page >= total_results:
                break
            
            start_index += response.results_per_page
        
        return all_vulnerabilities
    
    def fetch_cve(self, cve_id: str) -> Optional[Dict]:
        """
        Buscar um CVE específico.
        
        Args:
            cve_id: ID do CVE (ex: CVE-2021-44228)
            
        Returns:
            Dados do CVE ou None
        """
        response = self.fetch_page(cve_id=cve_id.upper())
        
        if response and response.vulnerabilities:
            return response.vulnerabilities[0]
        
        return None
    
    def generate_date_windows(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[tuple]:
        """
        Gerar janelas de 120 dias para full sync.
        
        Args:
            start_date: Data inicial
            end_date: Data final
            
        Returns:
            Lista de tuplas (start, end) de 120 dias cada
        """
        windows = []
        current = start_date
        
        while current < end_date:
            window_end = min(
                current + timedelta(days=self.MAX_DATE_RANGE_DAYS),
                end_date
            )
            windows.append((current, window_end))
            current = window_end + timedelta(seconds=1)
        
        return windows