from fastapi import FastAPI, HTTPException

from order_management.api_models import OrderData, PriceRequest, PriceResponse
from order_management.order_book import OrderBook
from order_management.orders import DuplicateOrder, InsufficientLiquidity, UnknownOrder


def create_app() -> FastAPI:
    app = FastAPI(title="Order Management System", version="1.0.0")
    book = OrderBook()

    @app.post(
        "/orders",
        status_code=201,
        response_model=OrderData,
        responses={409: {"description": "Order ID already exists"}},
    )
    def add_order(order: OrderData) -> OrderData:
        """Store/add an order; prevent duplicate order IDs."""
        try:
            book.add(order.to_order())
        except DuplicateOrder as exc:
            raise HTTPException(409, "Order ID already exists") from exc
        return order

    @app.delete(
        "/orders/{order_id}",
        status_code=204,
        responses={404: {"description": "Order ID does not exist"}},
    )
    def remove_order(order_id: int) -> None:
        """Remove a specific order."""
        try:
            book.remove(order_id)
        except UnknownOrder as exc:
            raise HTTPException(404, "Order ID does not exist") from exc

    @app.get("/orders/{order_id}", response_model=OrderData)
    def get_order(order_id: int) -> OrderData:
        try:
            return OrderData.from_order(book.get(order_id))
        except UnknownOrder as exc:
            raise HTTPException(404, "Order ID does not exist") from exc

    @app.post(
        "/prices",
        response_model=PriceResponse,
        responses={409: {"description": "Insufficient quantity"}},
    )
    def calculate_price(request: PriceRequest) -> PriceResponse:
        """Quote the price for the requested quantity."""
        try:
            total = book.calculate_price(request.symbol, request.side, request.amount)
        except InsufficientLiquidity as exc:
            raise HTTPException(409, str(exc)) from exc
        return PriceResponse(**request.model_dump(), total_price=total)

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
