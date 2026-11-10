"""Marshmallow schemas for request validation and response serialization."""

from marshmallow import Schema, ValidationError, fields, validate, validates


# ---------------------------------------------------------------------------
# Product Schemas (Lab 1)
# ---------------------------------------------------------------------------
class ProductOut(Schema):
    """Output schema for serializing a Product instance."""

    id = fields.Int(dump_only=True)
    sku = fields.Str()
    name = fields.Str()
    description = fields.Str(allow_none=True)
    price_cents = fields.Int()
    qty_in_stock = fields.Int()
    archived = fields.Bool()


class ProductIn(Schema):
    """Input validation schema for creating a new Product."""

    sku = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=32),
    )
    name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=255),
    )
    description = fields.Str(
        allow_none=True,
        load_default=None,
        validate=validate.Length(max=2000),
    )
    price_cents = fields.Int(
        required=True,
        validate=validate.Range(min=0),
    )
    qty_in_stock = fields.Int(
        load_default=0,
        validate=validate.Range(min=0),
    )

    @validates("name")
    def _validate_name(self, value: str, **kwargs) -> None:
        """Reject whitespace-only product names."""
        if value.strip() == "":
            raise ValidationError("Product name must not be blank.")


class ProductPatch(Schema):
    """Input validation schema for partially updating an existing Product."""

    name = fields.Str(validate=validate.Length(min=1, max=255))
    description = fields.Str(
        allow_none=True,
        validate=validate.Length(max=2000),
    )
    price_cents = fields.Int(validate=validate.Range(min=0))
    qty_in_stock = fields.Int(validate=validate.Range(min=0))

    @validates("name")
    def _validate_name(self, value: str, **kwargs) -> None:
        """Reject whitespace-only product names."""
        if value.strip() == "":
            raise ValidationError("Product name must not be blank.")


class ReserveIn(Schema):
    """Input validation schema for reserving product stock."""

    qty = fields.Int(
        required=True,
        validate=validate.Range(min=1),
    )


# ---------------------------------------------------------------------------
# Order & OrderItem Schemas (Homework Task 2)
# ---------------------------------------------------------------------------
class OrderItemIn(Schema):
    """Input schema for a single line item within an Order creation request."""

    product_id = fields.Int(
        required=True,
        validate=validate.Range(min=1),
    )
    qty = fields.Int(
        required=True,
        validate=validate.Range(min=1),
    )


class OrderIn(Schema):
    """Input schema for creating an Order with one or more OrderItem entries."""

    customer_name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=255),
    )
    items = fields.List(
        fields.Nested(OrderItemIn),
        required=True,
        validate=validate.Length(min=1),
    )

    @validates("customer_name")
    def _validate_customer_name(self, value: str, **kwargs) -> None:
        """Reject whitespace-only customer names."""
        if value.strip() == "":
            raise ValidationError("Customer name must not be blank.")


class OrderItemOut(Schema):
    """Output schema for an OrderItem including nested Product details."""

    id = fields.Int(dump_only=True)
    product_id = fields.Int()
    qty = fields.Int()
    unit_price_cents = fields.Int()
    product = fields.Nested(ProductOut, dump_only=True)


class OrderOut(Schema):
    """Output schema for an Order including all nested OrderItem entries."""

    id = fields.Int(dump_only=True)
    customer_name = fields.Str()
    status = fields.Str()
    total_cents = fields.Int()
    created_at = fields.DateTime(dump_only=True)
    items = fields.List(fields.Nested(OrderItemOut), dump_only=True)
