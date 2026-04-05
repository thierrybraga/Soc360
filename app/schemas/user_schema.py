"""
Open-Monitor User Schemas
Schemas for user data serialization and validation.
"""
from marshmallow import Schema, fields, validate, ValidationError, validates


class UserSchema(Schema):
    """
    Schema for user data serialization.
    """
    id = fields.Int(dump_only=True)
    email = fields.Email(required=True)
    is_active = fields.Boolean()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class UserCreateSchema(Schema):
    """
    Schema for user creation validation.
    """
    email = fields.Email(
        required=True,
        validate=validate.Length(max=255)
    )
    password = fields.Str(
        required=True,
        load_only=True,
        validate=validate.Length(min=8, error="Password must be at least 8 characters.")
    )

    @staticmethod
    def validate_password(password):
        if not any(char.isdigit() for char in password) or not any(char.isalpha() for char in password):
            raise ValidationError("Password must contain letters and numbers.")

    @validates('password')
    def _check_password(self, value):
        self.validate_password(value)


class UserLoginSchema(Schema):
    """
    Schema for user login validation.
    """
    email = fields.Email(required=True)
    password = fields.Str(
        required=True,
        load_only=True
    )
