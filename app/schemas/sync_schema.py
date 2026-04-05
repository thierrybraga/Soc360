"""
Open-Monitor Sync Schemas
Common schemas for synchronization metadata and API call logs.
"""
from marshmallow import Schema, fields


class SyncMetadataSchema(Schema):
    """
    Schema for serialization of synchronization metadata (SyncMetadata).
    """
    key = fields.Str(dump_only=True)
    value = fields.Str()


class ApiCallLogSchema(Schema):
    """
    Schema for serialization of API call logs (ApiCallLog).
    """
    id = fields.Int(dump_only=True)
    endpoint = fields.Str(required=True)
    status_code = fields.Int(required=True)
    response_time = fields.Float(required=True)
    timestamp = fields.DateTime(dump_only=True)
    sync_id = fields.Str(load_only=True)
    metadata = fields.Nested(SyncMetadataSchema, dump_only=True)