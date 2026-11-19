import pytest

from floorplan.geometry.scale import Dimension, bare_unit, estimate_scale, parse_length


@pytest.mark.parametrize(
    ("text", "metres"),
    [
        ("15'-3\"", 4.6482),
        ("15'3\"", 4.6482),
        ("4'-10\"", 1.4732),
        ("7'-0\"", 2.1336),
        ("12'", 3.6576),
        ("9'-4\"", 2.8448),
        ("8′-0″", 2.4384),
        ("3.5 m", 3.5),
        ("350 cm", 3.5),
        ("3500mm", 3.5),
    ],
)
def test_dimension_strings_parse_to_metres(text, metres):
    assert parse_length(text) == pytest.approx(metres, abs=1e-4)


def test_non_dimensions_are_ignored():
    assert parse_length("14'0\"X12'8\"") is None
    assert parse_length("BED ROOM") is None


def test_bare_numbers_take_the_sheets_unit():
    assert bare_unit(["415", "829", "1012"]) == "cm"
    assert parse_length("415", bare_unit(["415", "829"])) == pytest.approx(4.15)


def test_scale_is_the_median_and_misreads_are_reported():
    dimensions = [
        Dimension("10'", 150),
        Dimension("20'", 300),
        Dimension("5'", 75),
        Dimension("8'", 160),
    ]

    estimate = estimate_scale(dimensions)

    assert estimate.metres_per_unit == pytest.approx(0.3048 / 15)
    assert estimate.used == 3
    assert estimate.outliers == ["8'"]


def test_no_readable_dimensions_gives_no_scale():
    assert estimate_scale([Dimension("LIVING", 100)]) is None
