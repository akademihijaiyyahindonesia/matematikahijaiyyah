"""Test guard checks and audit detail for all 28 letters."""

from hijaiyyah.core.guards import compute_rho, compute_U, guard_check, guard_detail


class TestGuardCheck:
    def test_all_28_pass(self, all_entries):
        for e in all_entries:
            assert guard_check(e), f"Guard FAIL: {e.char} ({e.name})"

    def test_invalid_vector_rejected(self):
        bad = [0] * 18
        bad[14] = 99  # A_N = 99 but Na+Nb+Nd = 0
        assert not guard_check(bad)

    def test_negative_rho_rejected(self):
        bad = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0]
        # theta=1, Qc=1 → U=4, rho=1-4=-3 < 0
        assert not guard_check(bad)


class TestGuardDetail:
    def test_all_28_R1_through_R4_and_the_topological_pair(self, all_entries):
        for e in all_entries:
            d = guard_detail(e)
            for key in ("R1", "R2", "R3", "R4", "T1", "T2"):
                assert d[key], f"{e.char}: {key} failed"
            assert d["all_pass"]

    def test_detail_includes_U_and_rho(self, ba):
        d = guard_detail(ba)
        assert "U" in d
        assert "rho" in d
        assert d["rho"] == ba.theta_hat - d["U"]


class TestComputeU:
    def test_alif(self, alif):
        assert compute_U(list(alif.vector)) == 0

    def test_haa(self, haa):
        assert compute_U(list(haa.vector)) == 8  # 4*Qc = 4*2 = 8


class TestComputeRho:
    def test_non_negative_all_28(self, all_entries):
        for e in all_entries:
            rho = compute_rho(list(e.vector))
            assert rho >= 0, f"{e.char}: rho={rho}"


class TestNoCheckIsVacuous:
    """
    A check that cannot fail is not a check, and one of them could not.

    R5 read ``U == compute_U(vec)`` two lines after ``U = compute_U(vec)``.
    Over every letter, every component, every value in the nibble domain plus
    twenty thousand random vectors — 28,064 in all — R1 failed 21,490 times,
    R2 21,386, R3 22,503, R4 22,499, T1 1,497, T2 1,505, and R5 zero. It was
    counted among the audit relations, so the suite advertised seven where six
    were doing work.
    """

    def _corpus(self):
        import random

        from hijaiyyah.core.master_table import MASTER_TABLE

        for entry in MASTER_TABLE.all_entries():
            for component in range(18):
                for value in range(16):
                    vector = list(entry.vector)
                    vector[component] = value
                    yield vector
        rng = random.Random(4)
        for _ in range(4000):
            yield [rng.randrange(0, 16) for _ in range(18)]

    def test_every_reported_check_can_fail(self):
        from hijaiyyah.core.guards import guard_detail

        failures = {key: 0 for key in ("R1", "R2", "R3", "R4", "T1", "T2")}
        for vector in self._corpus():
            detail = guard_detail(vector)
            for key in failures:
                if not detail[key]:
                    failures[key] += 1

        vacuous = [key for key, count in failures.items() if count == 0]
        assert not vacuous, f"these can never fail, so they are not checks: {vacuous}"

    def test_the_seventh_is_only_reported_when_it_was_actually_run(self):
        """
        Reporting True for a test that did not run is how R5 survived. With no
        carried residue, R7 is None — not True.
        """
        from hijaiyyah.core.guards import compute_U, guard_detail

        vector = list(next(iter(self._corpus())))
        assert guard_detail(vector)["R7"] is None

        rho = vector[0] - compute_U(vector)
        assert guard_detail(vector, carried_rho=rho)["R7"] is True
        assert guard_detail(vector, carried_rho=rho + 1)["R7"] is False

    def test_the_language_evaluator_uses_the_same_implementation(self):
        """
        It used to carry its own copy, whose all_pass omitted T1 and T2 — so a
        vector failing a topological guard passed there and failed in
        core.guards. Two implementations of one check is how that happens.
        """
        from hijaiyyah.core.guards import guard_detail
        from hijaiyyah.language.evaluator import _guard_detail

        vector = [3, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0]
        assert _guard_detail(vector) == guard_detail(vector)
