"""Deterministic batches with configurable size and local identity mappings."""

from collections.abc import Iterator, Sequence

from .schemas import Customer


def make_batches(records: Sequence[Customer], batch_size: int) -> Iterator[tuple[Customer, ...]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive.")
    for start in range(0, len(records), batch_size):
        yield tuple(records[start:start + batch_size])
