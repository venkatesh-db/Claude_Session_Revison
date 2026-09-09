"""Tests for the cart service."""

import pytest

from src.cart import pricing
from src.cart.cart import OutOfStock, add_item, checkout, create_cart, items_in
from src.cart.catalog import ProductNotFound, current_price, search, stock_for
from src.cart.coupons import CouponInvalid, get_coupon, validate
from src.cart.db import init_db, reset

KURTA = "SKU-KURTA-01"
JEANS = "SKU-JEANS-04"
EMAIL = "test@example.com"
ADDRESS = "1 Test Street"


@pytest.fixture(autouse=True)
def clean_db(tmp_path):
    init_db(str(tmp_path / "test.db"))
    reset()
    yield


# ---------------------------------------------------------------- catalogue

def test_known_sku_has_a_price():
    assert current_price(KURTA) == 1299.00


def test_unknown_sku_raises():
    with pytest.raises(ProductNotFound):
        current_price("SKU-NOPE-99")


def test_search_finds_by_name():
    results = search("jeans")
    assert any(r["sku"] == JEANS for r in results)


def test_search_respects_max_price():
    results = search("", max_price=1000)
    assert all(r["price"] <= 1000 for r in results)


# ------------------------------------------------------------------ pricing

def test_subtotal_sums_line_totals():
    items = [
        {"qty": 2, "unit_price": 100.00},
        {"qty": 1, "unit_price": 50.00},
    ]
    assert pricing.subtotal(items) == 250.00


def test_tax_is_eighteen_percent():
    assert pricing.tax_on(1000.00) == 180.00


def test_discount_is_the_coupon_percentage():
    coupon = {"percent_off": 20.0}
    assert pricing.discount_for(1000.00, coupon) == 200.00


def test_no_coupon_means_no_discount():
    assert pricing.discount_for(1000.00, None) == 0.00


def test_totals_includes_every_component():
    items = [{"qty": 1, "unit_price": 1000.00}]
    result = pricing.totals(items)
    assert set(result) == {"subtotal", "discount", "tax", "total"}


# ------------------------------------------------------------------ coupons

def test_valid_coupon_passes():
    assert validate("FESTIVE20")["percent_off"] == 20.0


def test_expired_coupon_is_rejected():
    with pytest.raises(CouponInvalid):
        validate("EXPIRED5")


def test_unknown_coupon_is_rejected():
    with pytest.raises(CouponInvalid):
        validate("NOSUCHCODE")


def test_coupon_starts_unused():
    assert get_coupon("FESTIVE20")["uses"] == 0


# --------------------------------------------------------------------- cart

def test_new_cart_is_empty():
    cart_id = create_cart("user-1")
    assert items_in(cart_id) == []


def test_added_item_appears_in_the_cart():
    cart_id = create_cart("user-1")
    add_item(cart_id, JEANS, 2)
    items = items_in(cart_id)
    assert len(items) == 1
    assert items[0]["qty"] == 2


def test_checkout_returns_an_order_id():
    cart_id = create_cart("user-1")
    add_item(cart_id, JEANS, 1)
    order = checkout(cart_id, "user-1", EMAIL, ADDRESS)
    assert order["order_id"].startswith("OR")


def test_checkout_reduces_stock():
    before = stock_for(JEANS)
    cart_id = create_cart("user-1")
    add_item(cart_id, JEANS, 2)
    checkout(cart_id, "user-1", EMAIL, ADDRESS)
    assert stock_for(JEANS) == before - 2


def test_checkout_beyond_stock_is_rejected():
    cart_id = create_cart("user-1")
    add_item(cart_id, KURTA, 99)
    with pytest.raises(OutOfStock):
        checkout(cart_id, "user-1", EMAIL, ADDRESS)


def test_empty_cart_cannot_check_out():
    cart_id = create_cart("user-1")
    with pytest.raises(ValueError):
        checkout(cart_id, "user-1", EMAIL, ADDRESS)


def test_coupon_is_recorded_as_used():
    cart_id = create_cart("user-1")
    add_item(cart_id, JEANS, 1)
    checkout(cart_id, "user-1", EMAIL, ADDRESS, "FESTIVE20")
    assert get_coupon("FESTIVE20")["uses"] == 1
