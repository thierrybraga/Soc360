"""
Open-Monitor NVD Schemas
Schemas for NVD (National Vulnerability Database) data.
"""
from marshmallow import Schema, fields

from app.schemas.sync_schema import SyncMetadataSchema, ApiCallLogSchema


__all__ = ['SyncMetadataSchema', 'ApiCallLogSchema']
