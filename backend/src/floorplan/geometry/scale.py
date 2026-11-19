"""Works out a drawing's scale from its printed dimensions.

Each dimension the model reads gives its text (e.g. 15'-3", 3.5 m, 350) and its length in
drawing units. Parsing the text and dividing gives one metres-per-unit estimate per dimension;
the median is robust to a misread one, and estimates far from it are reported.
"""

import re
from dataclasses import dataclass
from statistics import median

FOOT = 0.3048
INCH = 0.0254
METRIC = {"m": 1.0, "cm": 0.01, "mm": 0.001}
OUTLIER = 0.08

_NUMBER = r"(\d+(?:[.,]\d+)?)"
_FEET_MARK = r"(?:'|′|’|ft)"
_INCH_MARK = r"(?:\"|″|”|''|in)"
_IMPERIAL = re.compile(rf"^{_NUMBER}\s*{_FEET_MARK}\s*-?\s*(?:{_NUMBER}\s*{_INCH_MARK}?)?$")
_INCHES = re.compile(rf"^{_NUMBER}\s*{_INCH_MARK}$")
_METRIC = re.compile(rf"^{_NUMBER}\s*(mm|cm|m)?$")


@dataclass(frozen=True)
class Dimension:
    text: str
    length: float


@dataclass(frozen=True)
class ScaleEstimate:
    metres_per_unit: float
    used: int
    outliers: list[str]


def parse_length(text: str, default_unit: str = "m") -> float | None:
    """Metres for a dimension string, or None if it isn't one."""
    cleaned = text.strip().lower().replace(" ", "")
    if match := _IMPERIAL.match(cleaned):
        feet, inches = match.groups()
        return _number(feet) * FOOT + (_number(inches) * INCH if inches else 0.0)
    if match := _INCHES.match(cleaned):
        return _number(match.group(1)) * INCH
    if match := _METRIC.match(cleaned):
        value, unit = match.groups()
        return _number(value) * METRIC[unit or default_unit]
    return None


def bare_unit(texts: list[str]) -> str:
    """The unit implied by unitless numbers: plans in cm or mm print values in the hundreds."""
    values = [_number(t) for t in texts if re.fullmatch(_NUMBER, t.strip())]
    if not values:
        return "m"
    typical = median(values)
    return "mm" if typical >= 1000 else "cm" if typical >= 50 else "m"


def estimate_scale(
    dimensions: list[Dimension], default_unit: str | None = None
) -> ScaleEstimate | None:
    unit = default_unit or bare_unit([d.text for d in dimensions])
    ratios = [
        (metres / d.length, d.text)
        for d in dimensions
        if d.length > 0 and (metres := parse_length(d.text, unit))
    ]
    if not ratios:
        return None
    middle = median(r for r, _ in ratios)
    kept = [r for r, _ in ratios if abs(r - middle) <= OUTLIER * middle]
    outliers = [text for r, text in ratios if abs(r - middle) > OUTLIER * middle]
    return ScaleEstimate(metres_per_unit=median(kept), used=len(kept), outliers=outliers)


def _number(text: str) -> float:
    return float(text.replace(",", "."))
