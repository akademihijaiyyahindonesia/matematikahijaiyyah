"""Wave 2 System-Programming Utilities in Native `.hcell` (HOS Syscall Clients).

Implements the four Wave 2 system utilities specified in the CosmicTera Engineering
Directive without modifying any kernel handler (`shell.hasm`, `hos.hasm`,
`hos_prog_load.hasm`), secure loader, boot path, or syscall ABI:

1. `w2_har_inspection` — HAR Inspection Utility:
   Queries canonical HAR vectors by index (`§(١)`, `§(٢٢)`, `§(٢٨)`), extracts
   anatomical & topological invariants (`Θ̂`, `A_K`, `H*`, `U`, `ρ`, `A_N`),
   verifies `⊢`, and streams results via official HOS `SYSCALL 1` (`⏣(١, val)`).
2. `w2_hfs_lifecycle` — HFS Lifecycle Client:
   Executes `HFS_CREATE` (`SYSCALL 6`), `HFS_WRITE` (`SYSCALL 8`), and
   `HFS_READ` (`SYSCALL 7` / `⛁(fid)`) for a composite `Kaf + Ba` vector (`H* = 1`),
   verifies 18-component equality (`CEQ` via `==`) and dynamic `H* == Ka` guard
   coupling on the read-back vector, and tests fail-closed rejection on duplicate
   or out-of-bounds file IDs.
3. `w2_overlay_verifier` — Overlay Verification Client:
   Invokes `LOAD_PROGRAM` (`SYSCALL 9` via `⏣(٩, id)`) for a valid verified
   overlay (`program_id = 1` -> `1`) and an absent/unverified slot
   (`program_id = 2` -> `0`), reporting status and codex signature via `SYSCALL 1`.
4. `w2_sys_diagnostics` — System Diagnostics Utility:
   Exercises HOS `SYSCALL 1` (`write`), `SYSCALL 2` (`read`), `SYSCALL 3` (`yield`),
   and fail-closed unknown `SYSCALL 99`, while auditing `H* == Ka` (`[17] == [7]`)
   and `Θ̂ == U + ρ` in user mode.
"""

from __future__ import annotations

from dataclasses import dataclass

from hijaiyyah.cells.hpg1_bridge import EndToEndPipelineResult, compile_and_execute_cells

W2_HAR_INSPECTION_UTILITY: str = """# الموج ٢ — فحص سجل الحروف (HAR Inspection Utility)
الف := §(١);
كاف := §(٢٢);
حرفي := §(٢٨);
⊢ الف;
⊢ كاف;
⊢ حرفي;
ط١ := ⏣(١, Θ̂(الف));
ط٢ := ⏣(١, كاف[١٥]);
ط٣ := ⏣(١, H*(كاف));
ط٤ := ⏣(١, U(حرفي));
ط٥ := ⏣(١, ρ(حرفي));
ط٦ := ⏣(١, حرفي[١٤]);
↦ ط١ + ط٢ + ط٣ + ط٤ + ط٥ + ط٦;
"""

W2_HFS_LIFECYCLE_CLIENT: str = """# الموج ٢ — عميل نظام الملفات (HFS Lifecycle Client)
كاف := §(٢٢);
حرفب := §(٢);
جمع := كاف + حرفب;
⊢ جمع;
فتح := ⏣(٦, ٠);
تكرار := ⏣(٦, ٠);
خارج := ⏣(٦, ٩);
حفظ := ⏣(٨, ٠, جمع);
ملف := ⛁(٠);
⊢ ملف;
تطابق := ملف == جمع;
ط١ := ⏣(١, فتح);
ط٢ := ⏣(١, تكرار);
ط٣ := ⏣(١, خارج);
ط٤ := ⏣(١, حفظ);
ط٥ := ⏣(١, تطابق);
ط٦ := ⏣(١, H*(ملف));
ط٧ := ⏣(١, Θ̂(ملف));
"""

W2_OVERLAY_VERIFICATION_CLIENT: str = """# الموج ٢ — التحقق من التراكب (Overlay Verifier)
سين := §(١٢);
كاف := §(٢٢);
مزيج := سين + كاف;
⊢ مزيج;
ح١ := ⏣(٩, ١);
ح٢ := ⏣(٩, ٢);
ط١ := ⏣(١, ح١);
ط٢ := ⏣(١, ح٢);
ط٣ := ⏣(١, Θ̂(مزيج));
ط٤ := ⏣(١, H*(مزيج));
"""

W2_SYSTEM_DIAGNOSTICS: str = """# الموج ٢ — تشخيص النظام وعقد الامان (System Diagnostics Utility)
الف := §(١);
حرفب := §(٢);
جيم := §(٥);
كاف := §(٢٢);
مجموع := الف + حرفب + جيم + كاف;
⊢ مجموع;
ح١ := ⏣(١, Θ̂(مجموع));
ح٢ := ⏣(٢, ٠);
ح٣ := ⏣(٣, ٠);
ح٩٩ := ⏣(٩٩, ٠);
تطابقكاف := مجموع[١٧] == مجموع[٧];
تطابقثيتا := Θ̂(مجموع) == (U(مجموع) + ρ(مجموع));
ط١ := ⏣(١, ح١);
ط٢ := ⏣(١, ح٢);
ط٣ := ⏣(١, ح٣);
ط٤ := ⏣(١, ح٩٩);
ط٥ := ⏣(١, تطابقكاف);
ط٦ := ⏣(١, تطابقثيتا);
"""


@dataclass(frozen=True)
class Wave2SyscallProgramSpec:
    """Formal specification and measured result for a Wave 2 `.hcell` system utility."""

    program_id: str
    title: str
    syscalls_exercised: tuple[int, ...]
    source: str
    expected_outputs: list[int]
    result: EndToEndPipelineResult


def run_wave2_syscalls(
    *, run_rtl: bool = True, run_rtl_loader: bool = True
) -> list[Wave2SyscallProgramSpec]:
    """Compile, verify (`4-B'`), and execute all four Wave 2 `.hcell` system utilities."""
    specs = [
        (
            "w2_har_inspection",
            "HAR Inspection Utility (§ + SYSCALL 1)",
            (1,),
            W2_HAR_INSPECTION_UTILITY,
            [0, 1, 1, 1, 2, 2, 6],
        ),
        (
            "w2_hfs_lifecycle",
            "HFS Lifecycle Client (SYSCALL 6, 7, 8 + CEQ + H* Check)",
            (1, 6, 7, 8),
            W2_HFS_LIFECYCLE_CLIENT,
            [1, 0, 0, 1, 1, 1, 4],
        ),
        (
            "w2_overlay_verifier",
            "Overlay Verification Client (SYSCALL 9 + SYSCALL 1)",
            (1, 9),
            W2_OVERLAY_VERIFICATION_CLIENT,
            [1, 0, 6, 1],
        ),
        (
            "w2_sys_diagnostics",
            "System Diagnostics (SYSCALL 1, 2, 3, 99 + Law H*-1 & Θ̂ Audit)",
            (1, 2, 3, 99),
            W2_SYSTEM_DIAGNOSTICS,
            [7, 1, 0, 1, 0, 1, 1],
        ),
    ]
    out: list[Wave2SyscallProgramSpec] = []
    for pid, title, syscalls, src, expected in specs:
        res = compile_and_execute_cells(
            src,
            use_native_letter_opcodes=True,
            reuse_registers=True,
            run_rtl=run_rtl,
            run_rtl_loader=(run_rtl_loader and pid == "w2_overlay_verifier"),
        )
        out.append(
            Wave2SyscallProgramSpec(
                program_id=pid,
                title=title,
                syscalls_exercised=syscalls,
                source=src,
                expected_outputs=expected,
                result=res,
            )
        )
    return out


__all__ = [
    "W2_HAR_INSPECTION_UTILITY",
    "W2_HFS_LIFECYCLE_CLIENT",
    "W2_OVERLAY_VERIFICATION_CLIENT",
    "W2_SYSTEM_DIAGNOSTICS",
    "Wave2SyscallProgramSpec",
    "run_wave2_syscalls",
]
