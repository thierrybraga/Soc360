"""
Open-Monitor Monitoring Schemas
Schemas for monitoring rules serialization and validation.
"""
from marshmallow import Schema, fields, validate


class MonitoringRuleSchema(Schema):
    """
    Schema for monitoring rules serialization and validation.
    """
    id = fields.Int(dump_only=True)
    user_id = fields.Int(
        required=True,
        validate=validate.Range(min=1, error="Invalid user ID.")
    )
    name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=255, error="Name must be between 1 and 255 characters.")
    )
    filter_params = fields.Dict(
        required=True,
        error_messages={"required": "Filter parameters are required."}
    )
    is_active = fields.Bool(
        required=True,
        error_messages={"required": "Active status is required."}
    )
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
