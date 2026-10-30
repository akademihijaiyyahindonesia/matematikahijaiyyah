# ============================================================================
# Test-HijaiyyahCells.ps1 — Reproducible PowerShell Host Test Runner
# (c) 2026 Maulana Amratulloh — HM-28-v.1.0-HC18D
# ============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Import-Module (Join-Path $PSScriptRoot 'HijaiyyahCells.psm1') -Force

Write-Host '=== 1. Master Table Audit (HM-28-v.1.0-HC18D) ==='
$mt = Import-HijaiyyahMasterTable
if ($mt.dataset_id -ne 'HM-28-v.1.0-HC18D') { throw "Unexpected dataset_id: $($mt.dataset_id)" }
if ($mt.letters.Count -ne 28) { throw "Expected 28 letters, got $($mt.letters.Count)" }
if (-not $mt.audit_summary.json_seal_verified) { throw 'JSON seal verification failed' }
if (-not $mt.audit_summary.rom_seal_verified) { throw 'ROM seal verification failed' }
Write-Host "  OK: 28 letters, JSON seal $($mt.seals.canonical_json_sha256.Substring(0,16))..., ROM seal $($mt.seals.canonical_rom_sha256.Substring(0,16))..."

Write-Host '=== 2. Symbol Lookup (Jim ج) ==='
$jim = Get-HijaiyyahSymbol -Symbol 'ج'
if ($jim.index -ne 5 -or $jim.B_U -ne 0 -or $jim.R_rho -ne 3 -or $jim.native_opcode -ne '0xE4') {
    throw "Unexpected Jim record: $($jim | ConvertTo-Json -Compress)"
}
Write-Host "  OK: Jim index=$($jim.index), U=$($jim.B_U), rho=$($jim.R_rho), opcode=$($jim.native_opcode)"

Write-Host '=== 3. Native .hcell End-to-End Benchmark (ب + س + م -> 10, 6, 4, 112, 9) ==='
$hcellSource = @"
بسم := ب + س + م;
⊢ بسم;
↦ Θ̂(بسم);
↦ U(بسم);
↦ ρ(بسم);
↦ ‖بسم‖²;
↦ d₂²(ب, م);
"@
$res = Invoke-HijaiyyahCellProgram -Source $hcellSource
$expected = @(10, 6, 4, 112, 9)
if (($res.outputs -join ',') -ne ($expected -join ',')) {
    throw "Expected outputs 10,6,4,112,9 but got $($res.outputs -join ',')"
}
if (-not $res.verify_4b_prime_ok -or -not $res.three_way_parity) {
    throw "4-B' verification or 3-way parity failed"
}
Write-Host "  OK: Outputs = $($res.outputs -join ', '), 4-B' = $($res.verify_4b_prime_reason), Parity = $($res.three_way_parity)"
Write-Host 'ALL POWERSHELL HOST CHECKS PASSED!'
