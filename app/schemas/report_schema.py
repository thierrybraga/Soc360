"""
SOC360 Report Schemas
Schemas for report-related data.
"""
from marshmallow import Schema, fields

from app.schemas.sync_schema import SyncMetadataSchema, ApiCallLogSchema


__all__ = ['SyncMetadataSchema', 'ApiCallLogSchema']
