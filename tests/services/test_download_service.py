"""
Tests for DownloadService.

Per SPEC_v3 Section 11.4: Handle model downloads with retry, progress, and verification.
"""

import os
import pytest
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock
from typing import Generator

import requests

from src.services.download_service import (
    DownloadService,
    DownloadTask,
    DownloadResult,
    DownloadError,
    HashMismatchError,
    DownloadTimeoutError,
)


class TestDownloadServiceBasic:
    """Basic download service functionality tests."""

    def test_download_task_dataclass(self) -> None:
        """DownloadTask should hold download parameters."""
        task = DownloadTask(
            url="https://example.com/file.bin",
            dest_path="/tmp/file.bin",
            expected_hash="abc123",
            priority=1
        )
        assert task.url == "https://example.com/file.bin"
        assert task.dest_path == "/tmp/file.bin"
        assert task.expected_hash == "abc123"
        assert task.priority == 1

    def test_download_task_defaults(self) -> None:
        """DownloadTask should have sensible defaults."""
        task = DownloadTask(url="https://example.com/file.bin", dest_path="/tmp/file.bin")
        assert task.expected_hash is None
        assert task.priority == 0

    def test_download_result_dataclass(self) -> None:
        """DownloadResult should hold result information."""
        result = DownloadResult(
            url="https://example.com/file.bin",
            dest_path="/tmp/file.bin",
            success=True,
            bytes_downloaded=1024
        )
        assert result.success is True
        assert result.error is None
        assert result.bytes_downloaded == 1024

    def test_download_result_failure(self) -> None:
        """DownloadResult should capture error information."""
        result = DownloadResult(
            url="https://example.com/file.bin",
            dest_path="/tmp/file.bin",
            success=False,
            error="Connection timeout"
        )
        assert result.success is False
        assert result.error == "Connection timeout"


class TestExceptions:
    """Test custom exception classes."""

    def test_download_error_base(self) -> None:
        """DownloadError should be base exception."""
        error = DownloadError("Download failed")
        assert str(error) == "Download failed"
        assert isinstance(error, Exception)

    def test_hash_mismatch_error(self) -> None:
        """HashMismatchError should inherit from DownloadError."""
        error = HashMismatchError("Hash mismatch: expected abc, got xyz")
        assert isinstance(error, DownloadError)

    def test_download_timeout_error(self) -> None:
        """DownloadTimeoutError should inherit from DownloadError."""
        error = DownloadTimeoutError("Timeout after 30s")
        assert isinstance(error, DownloadError)


class TestHashVerification:
    """Tests for SHA256 hash verification."""

    def test_verify_hash_valid(self) -> None:
        """verify_hash should return True for matching hash."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            content = b"test content for hashing"
            f.write(content)
            f.flush()
            temp_path = f.name

        try:
            expected_hash = hashlib.sha256(content).hexdigest()
            result = DownloadService.verify_hash(temp_path, expected_hash)
            assert result is True
        finally:
            os.unlink(temp_path)

    def test_verify_hash_invalid(self) -> None:
        """verify_hash should return False for mismatched hash."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            f.flush()
            temp_path = f.name

        try:
            result = DownloadService.verify_hash(temp_path, "invalid_hash")
            assert result is False
        finally:
            os.unlink(temp_path)

    def test_verify_hash_case_insensitive(self) -> None:
        """verify_hash should be case-insensitive."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            content = b"test"
            f.write(content)
            f.flush()
            temp_path = f.name

        try:
            expected_hash = hashlib.sha256(content).hexdigest()
            # Test uppercase version
            result = DownloadService.verify_hash(temp_path, expected_hash.upper())
            assert result is True
        finally:
            os.unlink(temp_path)

    def test_verify_hash_file_not_found(self) -> None:
        """verify_hash should return False for missing file."""
        result = DownloadService.verify_hash("/nonexistent/path/file.bin", "abc123")
        assert result is False


class TestGetFileSize:
    """Tests for get_file_size() remote file size check."""

    def test_get_file_size_success(self) -> None:
        """get_file_size should return content-length from headers."""
        with patch('requests.head') as mock_head:
            mock_response = MagicMock()
            mock_response.headers = {'content-length': '1048576'}
            mock_head.return_value = mock_response

            size = DownloadService.get_file_size("https://example.com/file.bin")
            assert size == 1048576

    def test_get_file_size_no_content_length(self) -> None:
        """get_file_size should return None if no content-length header."""
        with patch('requests.head') as mock_head:
            mock_response = MagicMock()
            mock_response.headers = {}
            mock_head.return_value = mock_response

            size = DownloadService.get_file_size("https://example.com/file.bin")
            assert size is None

    def test_get_file_size_timeout(self) -> None:
        """get_file_size should return None on timeout."""
        with patch('requests.head') as mock_head:
            mock_head.side_effect = requests.exceptions.Timeout()

            size = DownloadService.get_file_size("https://example.com/file.bin")
            assert size is None

    def test_get_file_size_request_error(self) -> None:
        """get_file_size should return None on request error (no silent exception)."""
        with patch('requests.head') as mock_head:
            mock_head.side_effect = requests.exceptions.ConnectionError()

            # Per ARCHITECTURE_PRINCIPLES: Returns None, not raises
            size = DownloadService.get_file_size("https://example.com/file.bin")
            assert size is None


class TestDownloadFile:
    """Tests for download_file() with retry logic."""

    def test_download_file_success(self) -> None:
        """download_file should successfully download and save file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = os.path.join(temp_dir, "subdir", "downloaded.bin")
            content = b"file content data"

            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.headers = {'content-length': str(len(content))}
                mock_response.iter_content.return_value = [content]
                mock_response.__enter__ = MagicMock(return_value=mock_response)
                mock_response.__exit__ = MagicMock(return_value=False)
                mock_get.return_value = mock_response

                result = DownloadService.download_file(
                    url="https://example.com/file.bin",
                    dest_path=dest_path
                )

                assert result is True
                assert os.path.exists(dest_path)
                with open(dest_path, 'rb') as f:
                    assert f.read() == content

    def test_download_file_creates_parent_dirs(self) -> None:
        """download_file should create parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = os.path.join(temp_dir, "a", "b", "c", "file.bin")

            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.headers = {'content-length': '5'}
                mock_response.iter_content.return_value = [b"test!"]
                mock_response.__enter__ = MagicMock(return_value=mock_response)
                mock_response.__exit__ = MagicMock(return_value=False)
                mock_get.return_value = mock_response

                result = DownloadService.download_file(
                    url="https://example.com/file.bin",
                    dest_path=dest_path
                )

                assert result is True
                assert os.path.exists(dest_path)

    def test_download_file_progress_callback(self) -> None:
        """download_file should call progress callback."""
        progress_calls = []

        def progress_cb(downloaded: int, total: int) -> None:
            progress_calls.append((downloaded, total))

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = os.path.join(temp_dir, "file.bin")

            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.headers = {'content-length': '30'}
                mock_response.iter_content.return_value = [b"0123456789"] * 3
                mock_response.__enter__ = MagicMock(return_value=mock_response)
                mock_response.__exit__ = MagicMock(return_value=False)
                mock_get.return_value = mock_response

                DownloadService.download_file(
                    url="https://example.com/file.bin",
                    dest_path=dest_path,
                    progress_callback=progress_cb
                )

                # Should have 3 progress updates
                assert len(progress_calls) == 3
                assert progress_calls[-1][0] == 30  # Final downloaded bytes

    def test_download_file_hash_verification_pass(self) -> None:
        """download_file should verify hash when provided."""
        content = b"content with known hash"
        expected_hash = hashlib.sha256(content).hexdigest()

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = os.path.join(temp_dir, "file.bin")

            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.headers = {'content-length': str(len(content))}
                mock_response.iter_content.return_value = [content]
                mock_response.__enter__ = MagicMock(return_value=mock_response)
                mock_response.__exit__ = MagicMock(return_value=False)
                mock_get.return_value = mock_response

                result = DownloadService.download_file(
                    url="https://example.com/file.bin",
                    dest_path=dest_path,
                    expected_hash=expected_hash
                )

                assert result is True

    def test_download_file_hash_mismatch_raises(self) -> None:
        """download_file should raise HashMismatchError on hash mismatch."""
        content = b"some content"

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = os.path.join(temp_dir, "file.bin")

            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.headers = {'content-length': str(len(content))}
                mock_response.iter_content.return_value = [content]
                mock_response.__enter__ = MagicMock(return_value=mock_response)
                mock_response.__exit__ = MagicMock(return_value=False)
                mock_get.return_value = mock_response

                with pytest.raises(HashMismatchError):
                    DownloadService.download_file(
                        url="https://example.com/file.bin",
                        dest_path=dest_path,
                        expected_hash="wrong_hash_value"
                    )

    def test_download_file_retry_on_timeout(self) -> None:
        """download_file should retry on timeout."""
        content = b"success after retry"

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = os.path.join(temp_dir, "file.bin")

            with patch('requests.get') as mock_get:
                # First call times out, second succeeds
                mock_response = MagicMock()
                mock_response.headers = {'content-length': str(len(content))}
                mock_response.iter_content.return_value = [content]
                mock_response.__enter__ = MagicMock(return_value=mock_response)
                mock_response.__exit__ = MagicMock(return_value=False)

                mock_get.side_effect = [
                    requests.exceptions.Timeout(),
                    mock_response
                ]

                with patch('time.sleep'):  # Skip actual sleep
                    result = DownloadService.download_file(
                        url="https://example.com/file.bin",
                        dest_path=dest_path
                    )

                assert result is True
                assert mock_get.call_count == 2

    def test_download_file_max_retries_exceeded(self) -> None:
        """download_file should return False after max retries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = os.path.join(temp_dir, "file.bin")

            with patch('requests.get') as mock_get:
                mock_get.side_effect = requests.exceptions.Timeout()

                with patch('time.sleep'):  # Skip actual sleep
                    result = DownloadService.download_file(
                        url="https://example.com/file.bin",
                        dest_path=dest_path
                    )

                assert result is False
                assert mock_get.call_count == DownloadService.MAX_RETRIES


class TestDownloadQueue:
    """Tests for concurrent download queue."""

    def test_download_queue_single_task(self) -> None:
        """download_queue should handle single task."""
        content = b"single file content"

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = os.path.join(temp_dir, "file.bin")
            task = DownloadTask(url="https://example.com/file.bin", dest_path=dest_path)

            with patch.object(DownloadService, 'download_file', return_value=True):
                with patch('os.path.getsize', return_value=len(content)):
                    service = DownloadService()
                    results = service.download_queue([task])

            assert len(results) == 1
            assert results[0].success is True

    def test_download_queue_multiple_tasks(self) -> None:
        """download_queue should handle multiple concurrent tasks."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks = [
                DownloadTask(
                    url=f"https://example.com/file{i}.bin",
                    dest_path=os.path.join(temp_dir, f"file{i}.bin")
                )
                for i in range(3)
            ]

            with patch.object(DownloadService, 'download_file', return_value=True):
                with patch('os.path.getsize', return_value=100):
                    service = DownloadService()
                    results = service.download_queue(tasks)

            assert len(results) == 3
            assert all(r.success for r in results)

    def test_download_queue_priority_ordering(self) -> None:
        """download_queue should process by priority (lower = higher priority)."""
        download_order = []

        def mock_download_file(url: str, dest_path: str, **kwargs) -> bool:
            download_order.append(url)
            return True

        with tempfile.TemporaryDirectory() as temp_dir:
            tasks = [
                DownloadTask(url="https://example.com/low.bin",
                            dest_path=os.path.join(temp_dir, "low.bin"), priority=10),
                DownloadTask(url="https://example.com/high.bin",
                            dest_path=os.path.join(temp_dir, "high.bin"), priority=0),
                DownloadTask(url="https://example.com/med.bin",
                            dest_path=os.path.join(temp_dir, "med.bin"), priority=5),
            ]

            with patch.object(DownloadService, 'download_file', side_effect=mock_download_file):
                with patch('os.path.getsize', return_value=100):
                    service = DownloadService()
                    service.download_queue(tasks, max_concurrent=1)

            # With max_concurrent=1, should be in priority order
            assert download_order[0] == "https://example.com/high.bin"
            assert download_order[1] == "https://example.com/med.bin"
            assert download_order[2] == "https://example.com/low.bin"

    def test_download_queue_partial_failure(self) -> None:
        """download_queue should capture individual task failures."""
        call_count = 0

        def mock_download_file(url: str, dest_path: str, **kwargs) -> bool:
            nonlocal call_count
            call_count += 1
            if "fail" in url:
                return False
            return True

        with tempfile.TemporaryDirectory() as temp_dir:
            tasks = [
                DownloadTask(url="https://example.com/success.bin",
                            dest_path=os.path.join(temp_dir, "success.bin")),
                DownloadTask(url="https://example.com/fail.bin",
                            dest_path=os.path.join(temp_dir, "fail.bin")),
            ]

            with patch.object(DownloadService, 'download_file', side_effect=mock_download_file):
                with patch('os.path.getsize', return_value=100):
                    service = DownloadService()
                    results = service.download_queue(tasks)

            assert len(results) == 2
            successes = [r for r in results if r.success]
            failures = [r for r in results if not r.success]
            assert len(successes) == 1
            assert len(failures) == 1

    def test_download_queue_hash_mismatch_captured(self) -> None:
        """download_queue should capture hash mismatch errors."""
        def mock_download_file(url: str, dest_path: str, **kwargs) -> bool:
            raise HashMismatchError("Hash mismatch for test file")

        with tempfile.TemporaryDirectory() as temp_dir:
            task = DownloadTask(
                url="https://example.com/file.bin",
                dest_path=os.path.join(temp_dir, "file.bin"),
                expected_hash="expected_hash"
            )

            with patch.object(DownloadService, 'download_file', side_effect=mock_download_file):
                service = DownloadService()
                results = service.download_queue([task])

            assert len(results) == 1
            assert results[0].success is False
            assert "Hash mismatch" in results[0].error


class TestResumeSupport:
    """Tests for download resume functionality via Range headers."""

    def test_download_resume_sends_range_header(self) -> None:
        """download_file should send Range header for partial files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = os.path.join(temp_dir, "file.bin")
            temp_path = dest_path + ".tmp"

            # Create partial temp file
            with open(temp_path, 'wb') as f:
                f.write(b"partial content")  # 15 bytes

            remaining_content = b" and more"

            with patch('requests.get') as mock_get:
                mock_response = MagicMock()
                mock_response.headers = {'content-length': str(len(remaining_content))}
                mock_response.iter_content.return_value = [remaining_content]
                mock_response.__enter__ = MagicMock(return_value=mock_response)
                mock_response.__exit__ = MagicMock(return_value=False)
                mock_get.return_value = mock_response

                DownloadService.download_file(
                    url="https://example.com/file.bin",
                    dest_path=dest_path
                )

                # Check Range header was sent
                call_kwargs = mock_get.call_args[1]
                assert 'headers' in call_kwargs
                assert 'Range' in call_kwargs['headers']
                assert call_kwargs['headers']['Range'] == 'bytes=15-'


class TestConstants:
    """Tests for service constants."""

    def test_max_retries_is_reasonable(self) -> None:
        """MAX_RETRIES should be a reasonable value."""
        assert DownloadService.MAX_RETRIES >= 2
        assert DownloadService.MAX_RETRIES <= 10

    def test_chunk_size_is_reasonable(self) -> None:
        """CHUNK_SIZE should be reasonable for large files."""
        # Should be at least 64KB for performance
        assert DownloadService.CHUNK_SIZE >= 65536
        # Should be at most 16MB to avoid memory issues
        assert DownloadService.CHUNK_SIZE <= 16 * 1024 * 1024

    def test_default_timeout_is_reasonable(self) -> None:
        """DEFAULT_TIMEOUT should be reasonable."""
        assert DownloadService.DEFAULT_TIMEOUT >= 10
        assert DownloadService.DEFAULT_TIMEOUT <= 300

    def test_max_concurrent_is_reasonable(self) -> None:
        """MAX_CONCURRENT should balance speed and resource usage."""
        assert DownloadService.MAX_CONCURRENT >= 1
        assert DownloadService.MAX_CONCURRENT <= 10
