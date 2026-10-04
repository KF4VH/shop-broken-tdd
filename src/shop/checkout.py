"""Order checkout.

The rules live in `src/shop/specs/checkout.md` - read it first.
The function signatures and constants are fixed by the specification.
"""

from shop.money import percent_of

PROMO_CODES = {"WELCOME10": 10, "SUMMER15": 15, "VIP35": 35}
SUPPORTED_CITIES = ("msk", "spb")
MAX_DISCOUNT_PERCENT = 30
VAT_PERCENT = 20
SHIPPING_KOPEKS = 49_000
FREE_DELIVERY_FROM_KOPEKS = 500_000
TIER_DISCOUNTS = ((10, 5), (25, 10), (50, 15))
REQUIRED_LINE_KEYS = ("sku", "qty", "unit_price_kopecks")


def _parse_integer(value: str) -> int | None:
    normalized = value.strip()
    if not normalized:
        return None
    digits = normalized[1:] if normalized[0] in "+-" else normalized
    if not digits:
        return None
    for index, character in enumerate(digits):
        if character == "_":
            if (
                index == 0
                or index == len(digits) - 1
                or not digits[index - 1].isdecimal()
                or not digits[index + 1].isdecimal()
            ):
                return None
        elif not character.isdecimal():
            return None
    return int(normalized)


def _validate_line(line: dict[str, str], seen_skus: set[str]) -> str | None:
    if any(key not in line for key in REQUIRED_LINE_KEYS):
        return "Order line is missing a required key"
    sku = line["sku"]
    if not sku:
        return "SKU cannot be empty"
    if sku in seen_skus:
        return "SKU cannot be repeated"
    seen_skus.add(sku)
    quantity = _parse_integer(line["qty"])
    if quantity is None or quantity <= 0:
        return "Quantity must be a positive integer"
    price = _parse_integer(line["unit_price_kopecks"])
    if price is None or price < 0:
        return "Price must be a non-negative integer"
    return None


def validate_order(
    lines: list[dict[str, str]],
    promo_code: str = "",
    shipping_city: str = "",
) -> str | None:
    """Return a human readable reason why the order is invalid, or None if it is fine."""
    if not lines:
        return "Order must contain at least one line"
    seen_skus: set[str] = set()
    for line in lines:
        reason = _validate_line(line, seen_skus)
        if reason is not None:
            return reason
    if promo_code and promo_code not in PROMO_CODES:
        return "Unknown promo code"
    if shipping_city and shipping_city not in SUPPORTED_CITIES:
        return "Unsupported shipping city"
    return None


def calculate_order_total(
    lines: list[dict[str, str]],
    promo_code: str = "",
    shipping_city: str = "",
) -> int | None:
    """Return the order total in kopecks, or None if the order is invalid."""
    if validate_order(lines, promo_code, shipping_city) is not None:
        return None
    subtotal = 0
    total_quantity = 0
    for line in lines:
        quantity = int(line["qty"])
        total_quantity += quantity
        subtotal += quantity * int(line["unit_price_kopecks"])
    tier_discount_percent = 0
    for minimum_quantity, discount_percent in TIER_DISCOUNTS:
        if total_quantity >= minimum_quantity:
            tier_discount_percent = discount_percent
    promo_discount_percent = PROMO_CODES.get(promo_code, 0)
    discount_percent = min(max(tier_discount_percent, promo_discount_percent), MAX_DISCOUNT_PERCENT)
    discount = percent_of(subtotal, discount_percent)
    discounted_subtotal = subtotal - discount
    delivery = (
        SHIPPING_KOPEKS if shipping_city and discounted_subtotal < FREE_DELIVERY_FROM_KOPEKS else 0
    )
    base = discounted_subtotal + delivery
    return base + percent_of(base, VAT_PERCENT)
