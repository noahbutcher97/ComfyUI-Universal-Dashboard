"""
Unit tests for SYS-06: P2P Proxy Configuration.
Verifies that DownloadService correctly retrieves and applies proxy settings.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.services.download_service import DownloadService

class TestProxyConfiguration:
    """Tests for proxy retrieval and application."""

    def test_get_proxies_none(self):
        """Verify _get_proxies returns None when no proxies configured."""
        with patch("src.services.download_service.config_manager.get", return_value=None):
            assert DownloadService._get_proxies() is None

    def test_get_proxies_http_only(self):
        """Verify _get_proxies handles HTTP only."""
        def mock_get(key, default=None):
            if key == "network.http_proxy": return "http://proxy:8080"
            return None
            
        with patch("src.services.download_service.config_manager.get", side_effect=mock_get):
            proxies = DownloadService._get_proxies()
            assert proxies == {"http": "http://proxy:8080"}
            assert "https" not in proxies

    def test_get_proxies_both(self):
        """Verify _get_proxies handles both HTTP and HTTPS."""
        def mock_get(key, default=None):
            if key == "network.http_proxy": return "http://proxy:8080"
            if key == "network.https_proxy": return "https://proxy:8443"
            return None
            
        with patch("src.services.download_service.config_manager.get", side_effect=mock_get):
            proxies = DownloadService._get_proxies()
            assert proxies == {
                "http": "http://proxy:8080",
                "https": "https://proxy:8443"
            }

    @patch("requests.get")
    def test_download_file_applies_proxies(self, mock_get):
        """Verify download_file passes proxies to requests.get."""
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "100"}
        mock_response.iter_content.return_value = [b"data"]
        mock_get.return_value = mock_response
        
        proxy_config = {"http": "http://proxy:8080"}
        
        with patch("src.services.download_service.DownloadService._get_proxies", return_value=proxy_config):
            DownloadService.download_file("https://example.com/file", "test.bin")
            
            # Check the call args
            args, kwargs = mock_get.call_args
            assert kwargs["proxies"] == proxy_config

    @patch("requests.head")
    def test_get_file_size_applies_proxies(self, mock_head):
        """Verify get_file_size passes proxies to requests.head."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "100"}
        mock_head.return_value = mock_response
        
        proxy_config = {"https": "https://proxy:8443"}
        
        with patch("src.services.download_service.DownloadService._get_proxies", return_value=proxy_config):
            DownloadService.get_file_size("https://example.com/file")
            
            args, kwargs = mock_head.call_args
            assert kwargs["proxies"] == proxy_config
