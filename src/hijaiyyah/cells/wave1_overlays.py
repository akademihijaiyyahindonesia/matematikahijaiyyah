"""Priority 4 — Wave 1 System-Programming Overlays in Native Hijaiyyah Cells (.hcell).

Implements Wave 1 of the CosmicTera self-programming roadmap:
1. W1_MATH_OVERLAY: Mathematical user-mode overlay verifying conservation identity
   Theta_hat(h) == U(h) + rho(h) and guard closure across composite words.
2. W1_HISA_PARITY_UTILITY: HISA parity probe testing CGET, CU, CRHO, CMOD4,
   HNRM2, HDIST, HPACK, and HCRC across boundary letters (ا, ب, ك, هـ, ي).
3. W1_VECTRONOMETRY_PROBE: Vectronometry angular quantization probe testing
   Mod-4 closure (Theta_4), loop-carrying vs open-path letters, and primary residue.
4. W1_INTRAMETRIC_DISTANCE: Intrametric distance and inner-product program
   verifying the 14D polarization identity ||a + b||^2 - ||a||^2 - ||b||^2 == 2*<a, b>.
5. W1_CODEX_OPERATION_TEST: Codex structural & HISAB operation probe verifying
   Anasir sums (G1, G2, G3), phonological marker H* (Kaf vs Qaf), and HISAB frame words.

Every overlay is written in pure native `.hcell` (Option 2, zero Latin keywords),
compiled by `CellHISABackend`, packaged into an `HPG1` v2 container, verified by
the `4-B'` static verifier (`load_check(..., overlay=True)`), and executed across
`CellEvaluator`, `HISAMachine`, and `HCPU` RTL.
"""

from __future__ import annotations

from dataclasses import dataclass

from hijaiyyah.cells.hpg1_bridge import EndToEndPipelineResult, compile_and_execute_cells


@dataclass(frozen=True, slots=True)
class Wave1OverlaySpec:
    """Specification and expected reference outputs of one Wave 1 user-mode overlay."""

    overlay_id: str
    category: str
    title: str
    hcell_source: str
    expected_outputs: list[int]


WAVE1_OVERLAYS: tuple[Wave1OverlaySpec, ...] = (
    Wave1OverlaySpec(
        overlay_id="W1_MATH_OVERLAY",
        category="Mathematical User-Mode Overlay",
        title="Kekekalan Inhina (Θ̂ = U + ρ) & Aditivitas Monoid pada Kata المركب",
        hcell_source="""
        حكم := ح + ك + م;
        ⊢ حكم;
        ط := Θ̂(حكم);
        ب_ميزان := U(حكم);
        ر_باقي := ρ(حكم);
        فرق := ط - (ب_ميزان + ر_باقي);
        ↦ ط;
        ↦ ب_ميزان;
        ↦ ر_باقي;
        ↦ فرق;
        """,
        expected_outputs=[9, 4, 5, 0],
    ),
    Wave1OverlaySpec(
        overlay_id="W1_HISA_PARITY_UTILITY",
        category="HISA Parity Utility",
        title="Paritas Instruksi CGET, CU, CRHO, CMOD4, HNRM2, HDIST, HPACK, HCRC",
        hcell_source="""
        الف := ا;
        حرف_ب := ب;
        كاف := ك;
        حرف_ه := هـ;
        حرف_ي := ي;
        ⊢ حرف_ه;
        ↦ Θ̂(الف);
        ↦ U(حرف_ه);
        ↦ ρ(كاف);
        ↦ Θ₄(حرف_ه);
        ↦ H*(كاف);
        ↦ ‖حرف_ب‖²;
        ↦ d₂²(كاف, حرف_ي);
        """,
        expected_outputs=[0, 8, 2, 0, 1, 7, 8],
    ),
    Wave1OverlaySpec(
        overlay_id="W1_VECTRONOMETRY_PROBE",
        category="Vectronometry Probe",
        title="Probe Vektronometri: Kuantisasi Sudut π/2, Gerbang Mod-4, & Residu Putaran",
        hcell_source="""
        حلقه := هـ + م + و;
        مفتوح := ب + س;
        ⊢ حلقه;
        ⊢ مفتوح;
        ↦ Θ̂(حلقه);
        ↦ U(حلقه);
        ↦ ρ(حلقه);
        ↦ Θ₄(حلقة);
        ↦ Θ̂(مفتوح);
        ↦ Θ₄(مفتوح);
        """.replace("حلقة", "حلقه"),
        expected_outputs=[17, 17, 0, 1, 6, 2],
    ),
    Wave1OverlaySpec(
        overlay_id="W1_INTRAMETRIC_DISTANCE",
        category="Intrametric Distance Program",
        title="Geometri Intrametrik 14D: Jarak d₂², Norma ‖·‖², & Identitas Polarisasi ⟨·,·⟩",
        hcell_source="""
        اول := ب + ت;
        ثان := س + ش;
        جمع := اول + ثان;
        ⊢ جمع;
        ن١ := ‖اول‖²;
        ن٢ := ‖ثان‖²;
        ن_جمع := ‖جمع‖²;
        داخلي := ⟨اول, ثان⟩;
        فرق_قطبي := ن_جمع - (ن١ + ن٢ + (٢ * داخلي));
        ↦ ن١;
        ↦ ن٢;
        ↦ ن_جمع;
        ↦ داخلي;
        ↦ d₂²(اول, ثان);
        ↦ فرق_قطبي;
        """,
        expected_outputs=[29, 93, 206, 42, 38, 0],
    ),
    Wave1OverlaySpec(
        overlay_id="W1_CODEX_OPERATION_TEST",
        category="Codex Operation Test",
        title="Uji Operasi Codex: Anasir (AN, AK, AQ), Penanda H* (ك vs ق), & Konsistensi G1–G3",
        hcell_source="""
        كلمه := ق + ك + ف;
        ⊢ كلمه;
        مجموع_ن := كلمه[١] + كلمه[٢] + كلمه[٣];
        مجموع_ك := كلمه[٤] + كلمه[٥] + كلمه[٦] + كلمه[٧] + كلمه[٨];
        مجموع_ق := كلمه[٩] + كلمه[١٠] + كلمه[١١] + كلمه[١٢] + كلمه[١٣];
        ↦ كلمه[١٤] - مجموع_ن;
        ↦ كلمه[١٥] - مجموع_ك;
        ↦ كلمه[١٦] - مجموع_ق;
        ↦ H*(كلمه);
        ↦ H*(ق);
        """,
        expected_outputs=[0, 0, 0, 1, 0],
    ),
)


def run_wave1_overlays(
    *,
    run_rtl: bool = True,
    run_rtl_loader: bool = False,
) -> dict[str, EndToEndPipelineResult]:
    """Compile, verify (`4-B'`), and execute all 5 Wave 1 user-mode overlays."""
    results: dict[str, EndToEndPipelineResult] = {}
    for spec in WAVE1_OVERLAYS:
        res = compile_and_execute_cells(
            spec.hcell_source,
            run_rtl=run_rtl,
            run_rtl_loader=run_rtl_loader,
        )
        results[spec.overlay_id] = res
    return results


__all__ = [
    "WAVE1_OVERLAYS",
    "Wave1OverlaySpec",
    "run_wave1_overlays",
]
