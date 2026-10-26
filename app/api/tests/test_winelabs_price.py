"""Which WineLabs figure becomes the market price."""
from tasks.update_market_prices import pick_price


def seed(s):
    pass


def test_winelabs_price_inside_the_middle_half():
    assert pick_price({"winelabs_price": 267.47, "median_value": 304.48, "p25": 278.59, "p75": 350.22}) == 304.48
    assert pick_price({"winelabs_price": 290, "median_value": 304.48, "p25": 278.59, "p75": 350.22}) == 290


def test_implausible_winelabs_price_takes_the_median():
    # Roulot Vireuils 2023
    assert pick_price({"winelabs_price": 89.99, "median_value": 250.59, "p25": 97.15, "p75": 273.8}) == 250.59


def test_missing_figures():
    assert pick_price({"median_value": 120}) == 120
    assert pick_price({"winelabs_price": 99}) == 99
    assert pick_price({}) is None
