#Requires -Version 5.1
<#
Scientific Learning Skills - Windows deployment script.

Default: prepare THIS repository for Claude Code on Windows
  - .claude\skills  -> junction to ..\skills  (junction needs no admin rights,
    unlike symlinks, and stays readable from native Windows programs)
  - .claude\CLAUDE.md  <- copy of RULES.md (re-copy after RULES.md changes)
  - memory\* skill directories initialized

-Target <path>: deploy into ANOTHER project instead (the junction still points
back to this repository's skills\ directory, so repo updates propagate).

Why not symlinks: creating symlinks on Windows requires Developer Mode or an
administrator, and WSL-created symlinks on NTFS drives (via /mnt/...) are not
resolvable by native Windows programs (WinError 1920). Junctions avoid both.
#>
param(
    [string]$Target = ""
)

$ErrorActionPreference = "Stop"
$repo = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$dest = if ($Target) { Join-Path (Resolve-Path $Target).Path ".claude" } else { Join-Path $repo ".claude" }
$skillsSrc = Join-Path $repo "skills"

if (-not (Test-Path $skillsSrc)) {
    throw "skills\ directory not found under $repo"
}

New-Item -ItemType Directory -Force -Path $dest | Out-Null

$skillsLink = Join-Path $dest "skills"
if (Test-Path $skillsLink) {
    # Also covers a git-materialized plain-text symlink file from a Windows checkout.
    Remove-Item $skillsLink -Force -Recurse
}
cmd /c mklink /J "$skillsLink" "$skillsSrc" | Out-Null
if (-not (Test-Path (Join-Path $skillsLink "scientific-learning\SKILL.md"))) {
    throw "Junction created but skills are not readable through it: $skillsLink"
}

Copy-Item (Join-Path $repo "RULES.md") (Join-Path $dest "CLAUDE.md") -Force

$memoryRoot = if ($Target) { Join-Path (Resolve-Path $Target).Path "memory" } else { Join-Path $repo "memory" }
$memorySkills = @(
    "word-deep-dive", "text-memorizer", "zero-base-learning", "fuzzy-understanding",
    "deepening-learning", "problem-solving", "mistake-review", "study-plan-builder"
)
foreach ($skill in $memorySkills) {
    New-Item -ItemType Directory -Force -Path (Join-Path $memoryRoot $skill) | Out-Null
}

Write-Host "Deployed skills junction: $skillsLink -> $skillsSrc"
Write-Host "Copied CLAUDE.md to $dest (re-copy RULES.md after it changes)"
Write-Host "Initialized memory directories under $memoryRoot"
Write-Host "Start Claude Code in this project; Skills load automatically."
Write-Host "Review states: python -m learning_agent.memory.cli (see memory/review-engine.md)"
