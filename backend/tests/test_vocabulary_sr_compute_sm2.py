"""Unit tests for compute_sm2 (SM-2 spaced-repetition scheduler)."""

from __future__ import annotations

import pytest

from app.services.language_vocabulary_sr_service import compute_sm2


@pytest.mark.parametrize("quality", [0, 1, 2])
def test_failing_quality_resets_repetition_and_interval(quality):
    ease, interval, repetition = compute_sm2(
        ease_factor=2.5, interval_days=50, repetition_number=9, quality=quality
    )
    assert repetition == 0
    assert interval == 1


def test_failing_quality_lowers_ease_factor():
    ease, interval, repetition = compute_sm2(2.5, 50, 4, 2)
    assert ease == pytest.approx(2.18)
    assert interval == 1
    assert repetition == 0


def test_repetition_zero_gives_interval_one():
    ease, interval, repetition = compute_sm2(2.5, 99, 0, 5)
    assert interval == 1
    assert repetition == 1


def test_repetition_one_gives_interval_six():
    ease, interval, repetition = compute_sm2(2.5, 99, 1, 5)
    assert interval == 6
    assert repetition == 2


def test_repetition_two_or_more_multiplies_by_ease_and_rounds():
    ease, interval, repetition = compute_sm2(2.5, 10, 2, 5)
    assert interval == 25
    assert repetition == 3


def test_ease_factor_floor_is_1_3_from_failing_review():
    ease, interval, repetition = compute_sm2(1.35, 50, 9, 0)
    assert ease == pytest.approx(1.3)
    assert interval == 1
    assert repetition == 0
