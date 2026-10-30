# ============================================================================
# HijaiyyahCells.psm1 — Thin PowerShell Development Host for Hijaiyyah Cells
# (c) 2026 Maulana Amratulloh — HM-28-v.1.0-HC18D
# ============================================================================
#
# Architectural Principle (Owner Decision 4 & CosmicTera Rule R1):
# PowerShell is a host environment, NOT a second implementation of Matematika
# Hijaiyyah or a duplicate evaluator. Every dataset lookup, seal verification,
# native .hcell / .hc parse, Cell IR semantic check, reference evaluation, HISA
# compilation, HPG1 container build, 4-B' verification, and HCPU RTL simulation
# delegates directly to the canonical Python `hijaiyyah.cells` engine.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Script:RepoRoot = Split-Path -Parent $PSScriptRoot
$Script:SrcPath  = Join-Path $Script:RepoRoot 'src'

function Resolve-HijaiyyahPython {
    [CmdletBinding()]
    param()
    $candidates = @(
        '/Library/Frameworks/Python.framework/Versions/3.13/bin/python3',
        (Join-Path $Script:RepoRoot '.venv-mac/bin/python'),
        (Join-Path $Script:RepoRoot '.venv/bin/python'),
        'python3',
        'python'
    )
    foreach ($cmd in $candidates) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            return $cmd
        }
    }
    throw 'Python 3 interpreter not found for HijaiyyahCells host wrapper.'
}

function Invoke-HijaiyyahCellsCli {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )
    $py = Resolve-HijaiyyahPython
    $prevPythonPath = $env:PYTHONPATH
    try {
        $env:PYTHONPATH = $Script:SrcPath
        $rawOut = & $py -m hijaiyyah.cells @Arguments 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "hijaiyyah.cells CLI failed (exit $LASTEXITCODE): $($rawOut -join "`n")"
        }
        $jsonText = ($rawOut | Out-String).Trim()
        return ($jsonText | ConvertFrom-Json)
    }
    finally {
        $env:PYTHONPATH = $prevPythonPath
    }
}

function Import-HijaiyyahMasterTable {
    <#
    .SYNOPSIS
    Imports and audits the authoritative HM-28-v.1.0-HC18D Master Table dataset via the canonical Python engine.
    #>
    [CmdletBinding()]
    param()
    return (Invoke-HijaiyyahCellsCli -Arguments @('audit-dataset'))
}

function Get-HijaiyyahSymbol {
    <#
    .SYNOPSIS
    Looks up one of the 28 canonical Hijaiyyah symbols by Arabic glyph, Latin name, or 1..28 index.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true, Position = 0)]
        [string]$Symbol
    )
    return (Invoke-HijaiyyahCellsCli -Arguments @('lookup-symbol', $Symbol))
}

function Invoke-HijaiyyahCellProgram {
    <#
    .SYNOPSIS
    Compiles, verifies (4-B'), and executes a native .hcell (or .hc compatibility) program through the shared Cell IR pipeline.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true, Position = 0)]
        [string]$Source,

        [Parameter(Mandatory = $false)]
        [switch]$HCCompat,

        [Parameter(Mandatory = $false)]
        [switch]$SkipRtl
    )
    $cliArgs = @('run', '--source', $Source)
    if ($HCCompat) {
        $cliArgs += '--hc-compat'
    }
    if ($SkipRtl) {
        $cliArgs += '--no-rtl'
    }
    return (Invoke-HijaiyyahCellsCli -Arguments $cliArgs)
}

Export-ModuleMember -Function @(
    'Import-HijaiyyahMasterTable',
    'Get-HijaiyyahSymbol',
    'Invoke-HijaiyyahCellProgram'
)
