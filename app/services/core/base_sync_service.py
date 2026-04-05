"""
Open-Monitor Base Sync Service
Common logic for external data synchronization (NVD, EUVD, MITRE).
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Union
from enum import Enum

from app.models.system import SyncMetadata

logger = logging.getLogger(__name__)

class SyncStatus(str, Enum):
    IDLE = 'idle'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

class BaseSyncService:
    """
    Base service for synchronization.
    Handles progress tracking, stats, and metadata persistence.
    """
    
    def __init__(self, prefix: str):
        self.prefix = prefix
        self.stats = {
            'processed': 0,
            'inserted': 0,
            'updated': 0,
            'errors': 0,
            'total': 0,
            'skipped': 0
        }

    def _get_key(self, key: str) -> str:
        """Helper to get prefixed metadata key."""
        return f"{self.prefix}_sync_progress_{key}"

    def get_progress(self) -> Dict:
        """Retrieve current sync progress from metadata."""
        def _int(key, default=0):
            val = SyncMetadata.get(self._get_key(key))
            try:
                return int(val) if val is not None else default
            except (ValueError, TypeError):
                return default

        # Basic progress data
        progress = {
            'status': SyncMetadata.get(self._get_key('status')) or SyncStatus.IDLE.value,
            'message': SyncMetadata.get(self._get_key('message')),
            'processed': _int('processed'),
            'total': _int('total'),
            'inserted': _int('inserted'),
            'updated': _int('updated'),
            'errors': _int('errors'),
            'skipped': _int('skipped'),
            'started_at': SyncMetadata.get(self._get_key('started_at')),
            'last_updated': SyncMetadata.get(self._get_key('last_updated')),
            'error': SyncMetadata.get(self._get_key('error'))
        }

        # NVD Specific aliases (for compatibility with existing JS)
        if self.prefix == 'nvd':
            progress.update({
                'processed_cves': _int('processed_cves', progress['processed']),
                'total_cves': _int('total_cves', progress['total']),
            })

        return progress

    def _update_progress(self, **kwargs) -> None:
        """Persist multiple progress metadata fields at once."""
        data = {self._get_key(k): v for k, v in kwargs.items()}
        # Add last_updated timestamp to every update
        data[self._get_key('last_updated')] = datetime.now(timezone.utc).isoformat()
        SyncMetadata.set_multi(data)

    def start_sync(self, message: str = "Starting sync...") -> None:
        """Mark sync as running and reset stats."""
        self.stats = {k: 0 for k in self.stats}
        self._update_progress(
            status=SyncStatus.RUNNING.value,
            message=message,
            started_at=datetime.now(timezone.utc).isoformat(),
            error=None,
            **self.stats
        )

    def complete_sync(self, message: str = "Sync completed successfully") -> None:
        """Mark sync as completed and update last sync date."""
        self._update_progress(
            status=SyncStatus.COMPLETED.value,
            message=message,
            **self.stats
        )
        # Store global last sync date for this source
        SyncMetadata.set(f"{self.prefix}_last_sync_date", datetime.now(timezone.utc).isoformat())

    def fail_sync(self, error: str) -> None:
        """Mark sync as failed with error message."""
        logger.error(f"{self.prefix} sync failed: {error}")
        self._update_progress(
            status=SyncStatus.FAILED.value,
            error=error,
            message=f"Error: {error}"
        )

    def cancel_sync(self) -> None:
        """Mark sync as cancelled."""
        self._update_progress(
            status=SyncStatus.CANCELLED.value,
            message="Sync cancelled by user"
        )
