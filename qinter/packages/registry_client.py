"""
qinter/packages/registry_client.py
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Any, Dict, List, Optional
from qinter.utils.exceptions import PackageError
from qinter.config.settings import get_settings
import time
import logging

logger = logging.getLogger(__name__)


class RegistryClient:
    """Client for interacting with the Qinter package registry with retry logic."""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            allowed_methods=["HEAD", "GET", "OPTIONS"],  # New parameter name
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
            )
        
        # Create session with retry and timeout
        self.session = requests.Session()
        
        # Configure HTTP adapter with retry strategy
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set request headers
        self.session.headers.update({
            'User-Agent': f'Qinter/{self._get_qinter_version()}',
            'Accept': 'application/json',
            'Connection': 'keep-alive'
        })
        
        # Default timeout for all requests
        self.timeout = (10, 30)  # (connect_timeout, read_timeout)
        
        # Use configured registry URL
        self.registry_url = self.settings.registry_url
    
    def search_packs(self, query: str) -> List[Dict[str, Any]]:
        """Search for explanation packs with retry logic."""
        url = f"{self.registry_url}/api/v1/packages/search"
        params = {"q": query, "limit": 50}
        
        return self._make_request_with_retry("GET", url, params=params, operation="search")
    
    def get_pack_info(self, pack_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a pack with retry logic."""
        url = f"{self.registry_url}/api/v1/packages/{pack_name}"
        
        response_data = self._make_request_with_retry("GET", url, operation="get_info")
        return response_data if response_data != "NOT_FOUND" else None
    
    def download_pack(self, pack_name: str, version: str = "latest") -> Optional[str]:
        """Download a pack with retry logic and longer timeout."""
        url = f"{self.registry_url}/api/v1/packages/{pack_name}/download"
        params = {"version": version}
        
        # Use longer timeout for downloads
        download_timeout = (10, 60)  # Up to 60 seconds for download
        
        response_data = self._make_request_with_retry(
            "GET", url, params=params, 
            operation="download", 
            timeout=download_timeout
        )
        
        if response_data == "NOT_FOUND":
            return None
        
        return response_data.get("content") if isinstance(response_data, dict) else None
    
    def list_available_packs(self) -> List[Dict[str, Any]]:
        """List all available packs with retry logic."""
        url = f"{self.registry_url}/api/v1/packages"
        params = {"limit": 100, "sort": "downloads"}
        
        response_data = self._make_request_with_retry("GET", url, params=params, operation="list")
        
        if isinstance(response_data, dict) and "packages" in response_data:
            return response_data["packages"]
        return []
    
    def _make_request_with_retry(
        self, 
        method: str, 
        url: str, 
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        operation: str = "request",
        timeout: Optional[tuple] = None
    ) -> Any:
        """Make HTTP request with retry logic and proper error handling."""
        
        timeout = timeout or self.timeout
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Attempting {operation} request (attempt {attempt + 1}/{max_retries})")
                
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    timeout=timeout
                )
                
                # Handle different status codes
                if response.status_code == 200:
                    try:
                        return response.json()
                    except ValueError:
                        # If response is not JSON, return text content
                        return response.text
                        
                elif response.status_code == 404:
                    logger.warning(f"{operation} returned 404: {url}")
                    return "NOT_FOUND"
                    
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    time.sleep(retry_after)
                    continue
                    
                elif response.status_code >= 500:
                    # Server error - retry
                    logger.warning(f"Server error {response.status_code}, retrying...")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        raise PackageError(f"Server error {response.status_code} after {max_retries} retries")
                        
                else:
                    # Other client errors - don't retry
                    logger.error(f"Client error {response.status_code}: {response.text}")
                    raise PackageError(f"HTTP {response.status_code}: {response.text}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on {operation} request (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise PackageError(f"Request timeout after {max_retries} attempts")
                    
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error on {operation} request (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise PackageError(f"Connection failed after {max_retries} attempts")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request exception during {operation}: {e}")
                raise PackageError(f"Request failed: {str(e)}")
        
        raise PackageError(f"Request failed after {max_retries} attempts")
    
    def _get_qinter_version(self) -> str:
        """Get the current Qinter version."""
        try:
            from qinter.__version__ import __version__
            return __version__
        except ImportError:
            return "unknown"
    
    def test_connection(self) -> bool:
        """Test connection to the registry."""
        try:
            url = f"{self.registry_url}/health"
            response = self.session.get(url, timeout=(5, 10))
            return response.status_code == 200
        except Exception:
            return False


# Global registry client instance
_client = RegistryClient()

def get_registry_client() -> RegistryClient:
    """Get the global registry client instance."""
    return _client