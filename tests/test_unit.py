"""Tests unitaires pour les fonctions utilitaires."""
from inf349.routes import shipping_price_cents, TAX_RATES


def test_shipping_price_under_500g():
    assert shipping_price_cents(300) == 500


def test_shipping_price_exactly_500g():
    assert shipping_price_cents(500) == 500


def test_shipping_price_between_500g_and_2kg():
    assert shipping_price_cents(501) == 1000
    assert shipping_price_cents(1999) == 1000


def test_shipping_price_2kg_and_above():
    assert shipping_price_cents(2000) == 2500
    assert shipping_price_cents(5000) == 2500


def test_tax_rates_values():
    assert TAX_RATES["QC"] == 0.15
    assert TAX_RATES["ON"] == 0.13
    assert TAX_RATES["AB"] == 0.05
    assert TAX_RATES["BC"] == 0.12
    assert TAX_RATES["NS"] == 0.14


def test_tax_rates_provinces():
    assert set(TAX_RATES.keys()) == {"QC", "ON", "AB", "BC", "NS"}
