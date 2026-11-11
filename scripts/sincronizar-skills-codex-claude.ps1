<#
.SYNOPSIS
    Sincroniza las skills del proyecto entre la convencion de Codex (.codex/skills)
    y la de Claude Code (.claude/skills).

.DESCRIPTION
    Tu repo guarda las skills en .codex/skills (convención de Codex/Antigravity) y
    las referencia desde AGENTS.md. Claude Code, en cambio, sólo lee:
      - Personal:  %USERPROFILE%\.claude\skills\<nombre>\SKILL.md
      - Proyecto:  <proyecto>\.claude\skills\<nombre>\SKILL.md
    Este script copia cada skill de .codex/skills a .claude/skills para que Claude
    Code las detecte, sin romper la fuente original ni usar junctions (OneDrive
    no sigue junctions y puede generar errores de sincronización).

    Úsalo cada vez que crees o edites una skill en .codex/skills.

.EXAMPLE
    .\sincronizar-skills-codex-claude.ps1
    .\sincronizar-skills-codex-claude.ps1 -ProjectRoot "C:\ruta\otro\proyecto"
#>
[CmdletBinding()]
param(
    [string] $ProjectRoot = $PSScriptRoot,
    [switch] $Force
)

$ErrorActionPreference = "Stop"

$source = Join-Path $ProjectRoot ".codex\skills"
$target = Join-Path $ProjectRoot ".claude\skills"

if (-not (Test-Path $source)) {
    Write-Host "No existe la carpeta de skills de Codex: $source" -ForegroundColor Red
    exit 1
}

[void](New-Item -ItemType Directory -Force -Path $target)

$copied = 0; $updated = 0; $skipped = 0
Get-ChildItem $source -Directory | ForEach-Object {
    $skill = $_
    $skillFile = Join-Path $skill.FullName "SKILL.md"
    if (-not (Test-Path $skillFile)) { return }

    $destDir = Join-Path $target $skill.Name
    $destFile = Join-Path $destDir "SKILL.md"
    [void](New-Item -ItemType Directory -Force -Path $destDir)

    $needsCopy = $Force -or -not (Test-Path $destFile)
    if (-not $needsCopy) {
        $a = (Get-FileHash $skillFile -Algorithm SHA256).Hash
        $b = (Get-FileHash $destFile -Algorithm SHA256).Hash
        $needsCopy = $a -ne $b
    }

    if ($needsCopy) {
        Copy-Item -LiteralPath $skillFile -Destination $destFile -Force
        if (Test-Path $destFile) { $updated++ } else { $copied++ }
    }
    else { $skipped++ }

    # recursos extra (references/, scripts/, assets/)
    Get-ChildItem $skill.FullName -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $res = Join-Path $_.FullName "*"
        Copy-Item -Path $res -Destination $destDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "Skills sincronizadas en: $target" -ForegroundColor Green
Write-Host "  nuevas/actualizadas : $updated" -ForegroundColor Green
Write-Host "  sin cambios         : $skipped"
Write-Host ""
Write-Host "Reinicia Claude Code en ese proyecto para que detecte las skills." -ForegroundColor Cyan
