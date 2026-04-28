from __future__ import annotations

from typing import Iterable


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def extended_view_curve(
    x: float,
    strength: float,
    exponent: float,
    inflection_point: float,
    start_point: float,
    end_point: float,
    acceleration: float = 1.0,
) -> float:
    x = clamp(float(x), 0.0, 1.0)
    strength = clamp(float(strength), 0.0, 10.0)
    exponent = max(0.05, float(exponent))
    inflection_point = clamp(float(inflection_point), 0.001, 0.999)
    start_point = clamp(float(start_point), 0.0, 0.999)
    end_point = clamp(float(end_point), 0.001, 1.0)

    if end_point <= start_point:
        start_point = min(start_point, 0.998)
        end_point = min(1.0, start_point + 0.001)

    if x <= start_point:
        return 0.0
    if x >= end_point:
        return 1.0

    t = (x - start_point) / (end_point - start_point)
    if t <= inflection_point:
        y = (t / inflection_point) ** exponent * inflection_point
        return clamp(y * strength, 0.0, 1.0)

    u = (t - inflection_point) / (1.0 - inflection_point)
    y = inflection_point + (u ** max(0.05, float(acceleration))) * (1.0 - inflection_point)
    return clamp(y * strength, 0.0, 1.0)


def curve_points(config, count: int = 80) -> Iterable[tuple[float, float]]:
    samples = max(2, int(count))
    for index in range(samples):
        x = index / (samples - 1)
        y = extended_view_curve(
            x=x,
            strength=getattr(config, "extended_view_strength", 0.0) * getattr(config, "extended_view_blend", 1.0),
            exponent=getattr(config, "extended_view_exponent", 1.0),
            inflection_point=getattr(config, "extended_view_inflection_point", 0.5),
            start_point=getattr(config, "extended_view_start_point", 0.0),
            end_point=getattr(config, "extended_view_end_point", 1.0),
            acceleration=getattr(config, "extended_view_acceleration", 1.0),
        )
        yield x, y
