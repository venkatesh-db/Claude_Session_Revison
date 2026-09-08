"""
E-commerce order processing system.

Demonstrates SOLID principles and common design patterns:
- SRP: Order, InventoryService, and notification concerns are separate classes.
- OCP: new payment methods, discounts, or shipping rules plug in without editing existing code.
- LSP: any PaymentProcessor/DiscountStrategy subclass is a drop-in replacement.
- ISP: PaymentProcessor, InventoryService, and OrderObserver are each small, single-purpose
  interfaces rather than one fat interface.
- DIP: OrderService depends on abstractions (PaymentProcessor, InventoryService), injected at construction.

Patterns used: Strategy (payment, discount), Factory (payment processor creation),
Observer (order status notifications).
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum, auto
from typing import Protocol

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Domain errors
# --------------------------------------------------------------------------

class OrderError(Exception):
    """Base class for all order-domain errors."""


class InsufficientStockError(OrderError):
    def __init__(self, sku: str, requested: int, available: int) -> None:
        self.sku = sku
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for {sku}: requested {requested}, available {available}"
        )


class PaymentDeclinedError(OrderError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Payment declined: {reason}")


class InvalidOrderStateError(OrderError):
    def __init__(self, current: "OrderStatus", attempted: str) -> None:
        super().__init__(f"Cannot {attempted} an order in state {current.name}")


# --------------------------------------------------------------------------
# Value objects / entities
# --------------------------------------------------------------------------

class OrderStatus(Enum):
    PENDING = auto()
    PAID = auto()
    SHIPPED = auto()
    CANCELLED = auto()
    REFUNDED = auto()


@dataclass(frozen=True)
class LineItem:
    sku: str
    unit_price: Decimal
    quantity: int

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError(f"quantity must be positive, got {self.quantity}")
        if self.unit_price < 0:
            raise ValueError(f"unit_price cannot be negative, got {self.unit_price}")

    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass
class Order:
    """Encapsulates order state. Status transitions are only made through OrderService."""

    customer_email: str
    items: list[LineItem]
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def subtotal(self) -> Decimal:
        return sum((item.subtotal for item in self.items), Decimal("0"))


# --------------------------------------------------------------------------
# Strategy pattern: discounts
# --------------------------------------------------------------------------

class DiscountStrategy(ABC):
    @abstractmethod
    def apply(self, subtotal: Decimal) -> Decimal:
        """Return the discount amount (not the resulting total) for a given subtotal."""


class NoDiscount(DiscountStrategy):
    def apply(self, subtotal: Decimal) -> Decimal:
        return Decimal("0")


class PercentageDiscount(DiscountStrategy):
    def __init__(self, percent: Decimal) -> None:
        if not (0 <= percent <= 100):
            raise ValueError("percent must be between 0 and 100")
        self._percent = percent

    def apply(self, subtotal: Decimal) -> Decimal:
        return (subtotal * self._percent / Decimal("100")).quantize(Decimal("0.01"))


class ThresholdFreeShippingDiscount(DiscountStrategy):
    """No line-item discount; expresses a rule via a flat credit once a threshold is met."""

    def __init__(self, threshold: Decimal, shipping_cost: Decimal) -> None:
        self._threshold = threshold
        self._shipping_cost = shipping_cost

    def apply(self, subtotal: Decimal) -> Decimal:
        return self._shipping_cost if subtotal >= self._threshold else Decimal("0")


# --------------------------------------------------------------------------
# Strategy + Factory pattern: payment processing
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class PaymentResult:
    success: bool
    transaction_id: str | None = None
    failure_reason: str | None = None


class PaymentProcessor(ABC):
    @abstractmethod
    def charge(self, amount: Decimal, order_id: str) -> PaymentResult:
        ...

    @abstractmethod
    def refund(self, transaction_id: str, amount: Decimal) -> PaymentResult:
        ...


class CreditCardProcessor(PaymentProcessor):
    def __init__(self, gateway_client: "PaymentGatewayClient") -> None:
        self._gateway = gateway_client

    def charge(self, amount: Decimal, order_id: str) -> PaymentResult:
        response = self._gateway.authorize(amount=amount, reference=order_id)
        if not response.approved:
            return PaymentResult(success=False, failure_reason=response.decline_reason)
        return PaymentResult(success=True, transaction_id=response.transaction_id)

    def refund(self, transaction_id: str, amount: Decimal) -> PaymentResult:
        response = self._gateway.reverse(transaction_id=transaction_id, amount=amount)
        return PaymentResult(success=response.approved, transaction_id=transaction_id)


class PayPalProcessor(PaymentProcessor):
    def __init__(self, api_client: "PayPalClient") -> None:
        self._client = api_client

    def charge(self, amount: Decimal, order_id: str) -> PaymentResult:
        result = self._client.create_payment(amount=str(amount), invoice_id=order_id)
        if result.get("state") != "approved":
            return PaymentResult(success=False, failure_reason=result.get("error", "unknown"))
        return PaymentResult(success=True, transaction_id=result["id"])

    def refund(self, transaction_id: str, amount: Decimal) -> PaymentResult:
        result = self._client.refund_payment(payment_id=transaction_id, amount=str(amount))
        return PaymentResult(success=result.get("state") == "completed", transaction_id=transaction_id)


class PaymentMethod(Enum):
    CREDIT_CARD = "credit_card"
    PAYPAL = "paypal"


class PaymentProcessorFactory:
    """Centralizes construction so callers depend only on PaymentMethod + this factory."""

    def __init__(self) -> None:
        self._builders: dict[PaymentMethod, "callable[[], PaymentProcessor]"] = {}

    def register(self, method: PaymentMethod, builder) -> None:
        self._builders[method] = builder

    def create(self, method: PaymentMethod) -> PaymentProcessor:
        try:
            builder = self._builders[method]
        except KeyError as exc:
            raise ValueError(f"No processor registered for {method}") from exc
        return builder()


# Minimal stand-ins for external SDKs so this module is self-contained/testable.
@dataclass
class _GatewayResponse:
    approved: bool
    transaction_id: str | None = None
    decline_reason: str | None = None


class PaymentGatewayClient(Protocol):
    def authorize(self, amount: Decimal, reference: str) -> _GatewayResponse: ...
    def reverse(self, transaction_id: str, amount: Decimal) -> _GatewayResponse: ...


class PayPalClient(Protocol):
    def create_payment(self, amount: str, invoice_id: str) -> dict: ...
    def refund_payment(self, payment_id: str, amount: str) -> dict: ...


# --------------------------------------------------------------------------
# Interface segregation: small, focused protocols
# --------------------------------------------------------------------------

class InventoryService(ABC):
    @abstractmethod
    def reserve(self, sku: str, quantity: int) -> None:
        """Raise InsufficientStockError if quantity is unavailable."""

    @abstractmethod
    def release(self, sku: str, quantity: int) -> None:
        ...


class InMemoryInventoryService(InventoryService):
    def __init__(self, stock: dict[str, int]) -> None:
        self._stock = dict(stock)

    def reserve(self, sku: str, quantity: int) -> None:
        available = self._stock.get(sku, 0)
        if available < quantity:
            raise InsufficientStockError(sku, quantity, available)
        self._stock[sku] = available - quantity

    def release(self, sku: str, quantity: int) -> None:
        self._stock[sku] = self._stock.get(sku, 0) + quantity


class OrderObserver(Protocol):
    def on_status_changed(self, order: Order, previous: OrderStatus) -> None: ...


class EmailNotifier:
    def on_status_changed(self, order: Order, previous: OrderStatus) -> None:
        logger.info(
            "Emailing %s: order %s moved from %s to %s",
            order.customer_email, order.order_id, previous.name, order.status.name,
        )


class AuditLogObserver:
    def on_status_changed(self, order: Order, previous: OrderStatus) -> None:
        logger.info(
            "AUDIT order=%s %s->%s at %s",
            order.order_id, previous.name, order.status.name, datetime.now(timezone.utc).isoformat(),
        )


# --------------------------------------------------------------------------
# Application service: orchestrates the domain (depends only on abstractions)
# --------------------------------------------------------------------------

class OrderService:
    def __init__(
        self,
        inventory: InventoryService,
        payment_processor: PaymentProcessor,
        discount_strategy: DiscountStrategy | None = None,
        observers: list[OrderObserver] | None = None,
    ) -> None:
        self._inventory = inventory
        self._payment_processor = payment_processor
        self._discount_strategy = discount_strategy or NoDiscount()
        self._observers = list(observers or [])
        self._transactions: dict[str, str] = {}  # order_id -> transaction_id

    def add_observer(self, observer: OrderObserver) -> None:
        self._observers.append(observer)

    def place_order(self, order: Order) -> Order:
        if order.status is not OrderStatus.PENDING:
            raise InvalidOrderStateError(order.status, "place")

        reserved: list[LineItem] = []
        try:
            for item in order.items:
                self._inventory.reserve(item.sku, item.quantity)
                reserved.append(item)

            discount = self._discount_strategy.apply(order.subtotal)
            total = max(order.subtotal - discount, Decimal("0"))

            result = self._payment_processor.charge(total, order.order_id)
            if not result.success:
                raise PaymentDeclinedError(result.failure_reason or "unknown")

            self._transactions[order.order_id] = result.transaction_id
            self._transition(order, OrderStatus.PAID)
            return order

        except OrderError:
            for item in reserved:
                self._inventory.release(item.sku, item.quantity)
            raise

    def cancel_order(self, order: Order) -> Order:
        if order.status not in (OrderStatus.PENDING, OrderStatus.PAID):
            raise InvalidOrderStateError(order.status, "cancel")

        if order.status is OrderStatus.PAID:
            transaction_id = self._transactions.get(order.order_id)
            if transaction_id:
                self._payment_processor.refund(transaction_id, order.subtotal)

        for item in order.items:
            self._inventory.release(item.sku, item.quantity)

        self._transition(order, OrderStatus.CANCELLED)
        return order

    def ship_order(self, order: Order) -> Order:
        if order.status is not OrderStatus.PAID:
            raise InvalidOrderStateError(order.status, "ship")
        self._transition(order, OrderStatus.SHIPPED)
        return order

    def _transition(self, order: Order, new_status: OrderStatus) -> None:
        previous = order.status
        order.status = new_status
        for observer in self._observers:
            observer.on_status_changed(order, previous)


# --------------------------------------------------------------------------
# Example wiring (composition root)
# --------------------------------------------------------------------------

def _build_demo_service() -> OrderService:
    class _AlwaysApproveGateway:
        def authorize(self, amount: Decimal, reference: str) -> _GatewayResponse:
            return _GatewayResponse(approved=True, transaction_id=f"txn_{reference[:8]}")

        def reverse(self, transaction_id: str, amount: Decimal) -> _GatewayResponse:
            return _GatewayResponse(approved=True, transaction_id=transaction_id)

    factory = PaymentProcessorFactory()
    factory.register(PaymentMethod.CREDIT_CARD, lambda: CreditCardProcessor(_AlwaysApproveGateway()))

    inventory = InMemoryInventoryService(stock={"SKU-1": 10, "SKU-2": 5})
    service = OrderService(
        inventory=inventory,
        payment_processor=factory.create(PaymentMethod.CREDIT_CARD),
        discount_strategy=PercentageDiscount(Decimal("10")),
        observers=[EmailNotifier(), AuditLogObserver()],
    )
    return service


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    order_service = _build_demo_service()
    order = Order(
        customer_email="learninguser49@springxe.com",
        items=[
            LineItem(sku="SKU-1", unit_price=Decimal("19.99"), quantity=2),
            LineItem(sku="SKU-2", unit_price=Decimal("49.50"), quantity=1),
        ],
    )

    order_service.place_order(order)
    order_service.ship_order(order)
    print(f"Order {order.order_id} final status: {order.status.name}")
