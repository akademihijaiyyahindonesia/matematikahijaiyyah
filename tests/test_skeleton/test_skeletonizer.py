"""Zhang-Suen thinning (IC.1.21, Bab I) run on real pixel arrays.

Nothing in the suite ran this code before this file: it was called only
through data already extracted elsewhere, never on a binary image it thins
itself. These tests feed it synthetic shapes and check the pixels it
actually produces.
"""

from __future__ import annotations

import numpy as np

from hijaiyyah.skeleton.skeletonizer import zhang_suen_thinness


def test_a_thick_bar_thins_to_strictly_fewer_pixels_inside_the_original_region() -> None:
    bar = np.zeros((5, 9), dtype=np.uint8)
    bar[1:4, 1:8] = 1
    thin = zhang_suen_thinness(bar)

    assert thin.sum() > 0
    assert thin.sum() < bar.sum()
    # Every surviving pixel was foreground in the input -- thinning only
    # removes, it never adds.
    assert np.all(thin[bar == 0] == 0)


def test_thinning_is_a_fixed_point_on_an_already_thin_skeleton() -> None:
    line = np.zeros((3, 9), dtype=np.uint8)
    line[1, 1:8] = 1
    once = zhang_suen_thinness(line)
    twice = zhang_suen_thinness(once)
    assert np.array_equal(once, twice)


def test_a_hollow_ring_keeps_its_hole_after_thinning() -> None:
    """A thick annulus (Qc-style loop, IB.1.10) must not thin its hole shut --
    that would turn a closed loop into a filled disc, changing Qc's meaning."""
    size = 11
    ring = np.zeros((size, size), dtype=np.uint8)
    yy, xx = np.ogrid[:size, :size]
    dist = (yy - 5) ** 2 + (xx - 5) ** 2
    ring[(dist <= 16) & (dist >= 4)] = 1

    thin = zhang_suen_thinness(ring)

    assert thin[5, 5] == 0, "the hole must stay open"
    assert 0 < thin.sum() < ring.sum()


def test_a_shape_touching_the_border_leaves_that_row_untouched() -> None:
    """The algorithm scans range(1, rows-1) x range(1, cols-1) only -- a
    foreground pixel sitting on row 0 is never a removal candidate, so it
    survives untouched regardless of what thinning does to the interior."""
    block = np.ones((5, 5), dtype=np.uint8)
    thin = zhang_suen_thinness(block)

    assert np.array_equal(thin[0, :], block[0, :])
    assert np.array_equal(thin[-1, :], block[-1, :])
    assert np.array_equal(thin[:, 0], block[:, 0])
    assert np.array_equal(thin[:, -1], block[:, -1])
