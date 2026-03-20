from __future__ import annotations


def normalize_nominal_sample_rate_hz(value: object) -> float:
    sample_rate_hz = float(value)
    if sample_rate_hz <= 0:
        raise ValueError("nominal_sample_rate_hz must be positive")
    return sample_rate_hz


def normalize_chunk_size(value: object) -> int:
    chunk_size = int(value)
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    return chunk_size


def sample_period_ns(nominal_sample_rate_hz: float) -> int:
    return int(
        round(1_000_000_000 / normalize_nominal_sample_rate_hz(nominal_sample_rate_hz))
    )


def chunk_duration_ns(nominal_sample_rate_hz: float, chunk_size: int) -> int:
    return sample_period_ns(nominal_sample_rate_hz) * normalize_chunk_size(chunk_size)


def timer_interval_ms(nominal_sample_rate_hz: float, chunk_size: int) -> int:
    return max(
        1,
        int(
            round(
                (1000.0 * normalize_chunk_size(chunk_size))
                / normalize_nominal_sample_rate_hz(nominal_sample_rate_hz)
            )
        ),
    )
