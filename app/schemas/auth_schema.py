"""
SOC360 Auth Schemas
Schemas for authentication validation and responses.
"""
from marshmallow import Schema, fields, validate


class AuthRegisterSchema(Schema):
    """
    Schema for user registration data validation.
    """
    email = fields.Email(
        required=True,
        validate=validate.Length(max=255),
        error_messages={"required": "Email field is required."}
    )
    password = fields.Str(
        required=True,
        load_only=True,
        validate=validate.Length(min=8, error="Password must be at least 8 characters."),
        error_messages={"required": "Password field is required."}
    )
    confirm_password = fields.Str(
        required=True,
        load_only=True,
        validate=validate.Length(min=8),
        error_messages={"required": "Password confirmation is required."}
    )

    def validate(self, data, **kwargs):
        if data.get('password') != data.get('confirm_password'):
            raise validate.ValidationError({
                'confirm_password': ['Passwords do not match.']
            })
        return data


class AuthLoginSchema(Schema):
    """
    Schema for user login data validation.
    """
    email = fields.Email(
        required=True,
        error_messages={"required": "Email field is required."}
    )
    password = fields.Str(
        required=True,
        load_only=True,
        error_messages={"required": "Password field is required."}
    )


class AuthResponseSchema(Schema):
    """
    Schema for response after successful authentication.
    """
    id = fields.Int(dump_only=True)
    email = fields.Email(dump_only=True)
    is_active = fields.Boolean(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
