from dataclasses import asdict

from pydantic import BaseModel, ConfigDict, Field

from order_management.orders import Order, Side


class OrderData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Numeric fields reject coercion from strings or fractional values.
    order_id: int = Field(strict=True)
    symbol: str
    side: Side
    amount: int = Field(strict=True)
    price: int = Field(strict=True)

    def to_order(self) -> Order:
        """Create an order from the validated fields."""
        return Order(**self.model_dump())

    @classmethod
    def from_order(cls, order: Order) -> "OrderData":
        return cls(**asdict(order))


class PriceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    side: Side
    amount: int = Field(strict=True)


class PriceResponse(PriceRequest):
    """The requested quantity and its total price, rather than a unit price."""

    total_price: int
