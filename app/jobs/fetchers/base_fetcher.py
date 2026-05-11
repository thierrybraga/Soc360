"""
SOC360 Base Fetcher
Base class for HTTP fetchers with common retry and session setup.
"""
import logging
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class BaseFetcher:
    """
    Base class for HTTP fetchers.
    
    Provides common session setup with retry logic.
    """
    
    def __init__(self, timeout: int = 30, user_agent: str = 'SOC360/1.0'):
        self.timeout = timeout
        self.session = self._create_session(user_agent)
    
    def _create_session(self, user_agent: str) -> requests.Session:
        """Criar sessão HTTP com retry."""
        session = requests.Session()
        
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=['GET']
        )
        
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        
        session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'application/json'
        })
        
        return session