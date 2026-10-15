from core.version import Version, parse_version, satisfies_range


def test_parse_and_compare():
    assert parse_version("1.2.3") == Version(1, 2, 3)
    assert parse_version("v2.0.0") > parse_version("1.9.9")


def test_ranges():
    assert satisfies_range("1.4.0", "^1.2.3")
    assert not satisfies_range("2.0.0", "^1.2.3")
    assert satisfies_range("0.2.9", "^0.2.3")
    assert not satisfies_range("0.3.0", "^0.2.3")
    assert satisfies_range("1.2.9", "~1.2.3")
    assert not satisfies_range("1.3.0", "~1.2.3")
    assert satisfies_range("1.5.0", ">=1.0.0 <2.0.0")
    assert not satisfies_range("2.0.0", ">=1.0.0 <2.0.0")
    assert satisfies_range("3.1.0", ">=1.0.0 <2.0.0 || >=3.0.0")
    assert satisfies_range("1.2.3", "1.2.3")
    assert not satisfies_range("1.2.4", "1.2.3")
    assert satisfies_range("9.9.9", "*")
