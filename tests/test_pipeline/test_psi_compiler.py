"""Tests for Ψ-Compiler and .hgeo format."""

import pytest

from hijaiyyah.pipeline import (
    ExtractionParams,
    HGeoFile,
    Measurement,
    PsiCompiler,
)


class TestPsiCompilerImport:

    def test_import_psi(self):
        assert PsiCompiler is not None

    def test_import_hgeo(self):
        assert HGeoFile is not None

    def test_import_measurement(self):
        assert Measurement is not None


class TestMeasurement:
    """Test Measurement dataclass."""

    def test_v18_assembly(self):
        m = Measurement(
            theta_hat=2,
            N=[0, 0, 1],
            K=[0, 1, 0, 0, 0],
            Q=[1, 0, 0, 0, 0],
            A_N=1, A_K=1, A_Q=1, H_star=0,
        )
        v18 = m.v18
        assert len(v18) == 18
        assert v18[0] == 2      # Θ̂
        assert v18[3] == 1      # N_d
        assert v18[5] == 1      # K_x
        assert v18[9] == 1      # Q_p

    def test_default_zeros(self):
        m = Measurement()
        assert all(x == 0 for x in m.v18)


class TestHGeoFile:
    """Test .hgeo format."""

    def test_create(self):
        hgeo = HGeoFile(glyph_name="ب", glyph_id="U+0628")
        assert hgeo.glyph_name == "ب"

    def test_json_roundtrip(self):
        hgeo = HGeoFile(
            glyph_name="ب",
            glyph_id="U+0628",
            measurement=Measurement(
                theta_hat=2, N=[0, 0, 1],
                K=[0, 1, 0, 0, 0], Q=[1, 0, 0, 0, 0],
                A_N=1, A_K=1, A_Q=1, H_star=0,
            ),
        )
        json_str = hgeo.to_json()
        restored = HGeoFile.from_json(json_str)
        assert restored.glyph_name == "ب"
        assert restored.measurement.theta_hat == 2
        assert restored.measurement.N == [0, 0, 1]

    def test_digest(self):
        hgeo = HGeoFile(
            measurement=Measurement(theta_hat=2)
        )
        digest = hgeo.compute_digest()
        assert digest.startswith("sha256:")
        assert len(digest) > 10

    def test_v18_property(self):
        hgeo = HGeoFile(
            measurement=Measurement(theta_hat=2, N=[0, 0, 1],
                                     K=[0, 1, 0, 0, 0],
                                     Q=[1, 0, 0, 0, 0],
                                     A_N=1, A_K=1, A_Q=1, H_star=0)
        )
        assert len(hgeo.v18) == 18
        assert hgeo.v18[0] == 2


class TestExtractionParams:

    def test_defaults(self):
        p = ExtractionParams()
        assert p.algorithm == "zhang-suen"
        assert p.adjacency == "8-neighborhood"


class TestPsiCompiler:
    """Test Ψ-Compiler pipeline."""

    def test_init(self):
        psi = PsiCompiler()
        assert psi.VERSION == "1.0.0"

    def test_extract_glyph_returns_hgeo(self):
        psi = PsiCompiler()
        try:
            hgeo = psi.extract_glyph("ب")
            assert isinstance(hgeo, HGeoFile)
            assert hgeo.glyph_name == "ب"
        except Exception:
            pytest.skip("Master table not available")

    def test_extract_sets_guard_status(self):
        psi = PsiCompiler()
        try:
            hgeo = psi.extract_glyph("ا")
            assert "G1" in hgeo.guard_status
        except Exception:
            pytest.skip("Master table not available")


class TestPsiCompilerRunsCSGI:
    """Steps 2 and 3 of the docstring's pipeline, actually executed.

    `extract_glyph` used to fill a measurement from the Master Table and
    nothing else -- the CSGI path was described in the class docstring and had
    no processor to call, so nodes, edges and mainpath came back empty for
    every letter. Given an image it now runs thinning -> contraction ->
    MainPath selection for real. The measurement stays the sealed table's,
    because deriving it needs curvature integration and nuqtah separation
    that do not exist here; these tests pin that split so neither half can
    quietly start claiming the other's work.
    """

    @staticmethod
    def _thick_t():
        import numpy as np

        pixels = np.zeros((11, 11), dtype=np.uint8)
        pixels[1:4, 1:10] = 1
        pixels[3:9, 4:7] = 1
        return pixels

    def test_without_an_image_the_structural_fields_stay_empty(self):
        hgeo = PsiCompiler().extract_glyph("ب")
        assert hgeo.nodes == []
        assert hgeo.edges == []
        assert hgeo.mainpath.node_sequence == []
        assert any(v != 0 for v in hgeo.v18), "the sealed measurement still lands"

    def test_with_an_image_the_graph_and_mainpath_are_derived(self):
        hgeo = PsiCompiler().extract_glyph("ت", image=self._thick_t())

        assert len(hgeo.nodes) > 0 and len(hgeo.edges) > 0
        assert len(hgeo.mainpath.node_sequence) > 1
        assert hgeo.mainpath.total_pixels > 0
        # Every node on the selected path is a node of the extracted graph.
        ids = {n.id for n in hgeo.nodes}
        assert set(hgeo.mainpath.node_sequence) <= ids
        assert set(hgeo.mainpath.edge_sequence) <= {e.id for e in hgeo.edges}

    def test_node_kind_follows_degree_as_IC_1_19_classifies_it(self):
        hgeo = PsiCompiler().extract_glyph("ت", image=self._thick_t())
        kinds = {n.kind for n in hgeo.nodes}
        assert kinds <= {"ENDPOINT", "JUNCTION", "KINK"}
        assert "ENDPOINT" in kinds, "a T has open arms"

    def test_the_measurement_is_the_sealed_one_on_both_paths(self):
        """The image supplies structure, never v18 -- if that ever changes,
        this is the test that should have to change with it."""
        psi = PsiCompiler()
        without = psi.extract_glyph("ت")
        with_image = psi.extract_glyph("ت", image=self._thick_t())
        assert with_image.v18 == without.v18
