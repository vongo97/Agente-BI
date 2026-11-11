<#
.SYNOPSIS
    Instala Claude Code Skills desde GitHub (o las deja listadas) en el ámbito
    personal o de proyecto.

.DESCRIPTION
    Claude Code reconoce skills en:
      - Personal : %USERPROFILE%\.claude\skills\<nombre>\SKILL.md
      - Proyecto : <proyecto>\.claude\skills\<nombre>\SKILL.md
    Cada skill es una carpeta con un SKILL.md (frontmatter name + description) y,
    opcionalmente, scripts/, references/ y assets/.

    Este script descarga carpetas completas de skill desde cualquier repositorio
    de GitHub usando la API pública (sin token) y las deja listas para usar.

.EXAMPLE
    # Listar las skills del repo oficial de Anthropic
    .\instalar-skills.ps1 -Repo anthropics/skills -List

.EXAMPLE
    # Instalar 3 skills oficiales en el ámbito personal
    .\instalar-skills.ps1 -Repo anthropics/skills -Name pdf,xlsx,pptx -Scope personal

.EXAMPLE
    # Instalar una skill de un repo propio en un proyecto concreto
    .\instalar-skills.ps1 -Repo mi-org/mi-skills -Name vektra-protocol -Scope project `
        -Target "C:\ruta\proyecto"

.NOTES
    Sin token usa 60 peticiones/hora de la API pública de GitHub. Con -Token puedes
    subir el límite. El script no sobrescribe una skill existente salvo que uses -Force.
#>
[CmdletBinding(DefaultParameterSetName = "Install")]
param(
    [Parameter(Mandatory = $true)]
    [string] $Repo,

    [string] $Branch,

    [string] $Path = "skills",

    [string[]] $Name,

    [ValidateSet("personal", "project")]
    [string] $Scope = "personal",

    [string] $Target,

    [switch] $List,

    [switch] $Force,

    [string] $Token
)

$ErrorActionPreference = "Stop"
$api = "https://api.github.com"

function Invoke-Gh {
    param([string] $Uri)
    $headers = @{ "User-Agent" = "claude-skill-installer" }
    if ($Token) { $headers["Authorization"] = "Bearer $Token" }
    try {
        Invoke-RestMethod -Uri $Uri -Headers $headers -TimeoutSec 30
    }
    catch {
        throw "Fallo la API de GitHub ($Uri): $($_.Exception.Message)"
    }
}

# --- destino ---------------------------------------------------------------
if ($Scope -eq "personal") {
    $destRoot = Join-Path $env:USERPROFILE ".claude\skills"
}
else {
    if (-not $Target) { throw "Con -Scope project debes indicar -Target <ruta del proyecto>." }
    $destRoot = Join-Path $Target ".claude\skills"
}
[void](New-Item -ItemType Directory -Force -Path $destRoot)

# --- metadatos del repo ----------------------------------------------------
$repoInfo = Invoke-Gh "$api/repos/$Repo"
if (-not $Branch) { $Branch = $repoInfo.default_branch }
Write-Host "Repositorio : $Repo (rama $Branch)" -ForegroundColor Cyan
Write-Host "Destino     : $destRoot" -ForegroundColor Cyan
Write-Host ""

# --- modo listar -----------------------------------------------------------
if ($List) {
    $items = Invoke-Gh "$api/repos/$Repo/contents/${Path}?ref=$Branch"
    $skills = @()
    foreach ($item in $items) {
        if ($item.type -ne "dir") { continue }
        $hasSkill = Invoke-Gh "$api/repos/$Repo/contents/$($item.path)/SKILL.md?ref=$Branch" -ErrorAction SilentlyContinue
        if ($hasSkill) {
            $desc = ""
            try {
                $raw = Invoke-RestMethod -Uri "https://raw.githubusercontent.com/$Repo/$Branch/$($item.path)/SKILL.md" -TimeoutSec 20
                if ($raw -match '(?m)^description:\s*(.+)$') { $desc = $Matches[1].Trim('"', "'") }
            } catch { }
            $skills += [pscustomobject]@{ Nombre = $item.name; Ruta = $item.path; Descripcion = $desc }
        }
    }
    $skills | Format-Table -AutoSize -Wrap
    Write-Host "Total: $($skills.Count) skills en '$Path'." -ForegroundColor Green
    Write-Host ""
    Write-Host "Para instalar:  .\instalar-skills.ps1 -Repo $Repo -Name <nombre1,nombre2> -Scope $Scope" -ForegroundColor Cyan
    exit 0
}

if (-not $Name -or $Name.Count -eq 0) {
    throw "Indica -Name <skill1,skill2> para instalar, o usa -List para ver el catálogo."
}

# --- árbol del repo --------------------------------------------------------
$tree = Invoke-Gh "$api/repos/$Repo/git/trees/${Branch}?recursive=1"
if ($tree.truncated) { Write-Warning "El repo es enorme y el árbol vino truncado; puede faltar algún archivo." }
$blobs = @($tree.tree | Where-Object { $_.type -eq "blob" })

$installed = 0; $skipped = 0

foreach ($skillName in $Name) {
    $skillPath = "$Path/$skillName".Trim("/")
    $files = $blobs | Where-Object { $_.path -like "$skillPath/*" }
    if (-not $files) {
        Write-Warning "No se encontro la skill '$skillName' en '$skillPath' de $Repo."
        continue
    }
    if (-not ($files | Where-Object { $_.path -eq "$skillPath/SKILL.md" })) {
        Write-Warning "'$skillName' no tiene SKILL.md en la raiz; se omite."
        continue
    }

    $skillDir = Join-Path $destRoot $skillName
    if ((Test-Path $skillDir) -and -not $Force) {
        Write-Host "  [skip] $skillName ya existe (usa -Force para sobrescribir)" -ForegroundColor DarkYellow
        $skipped++
        continue
    }
    [void](New-Item -ItemType Directory -Force -Path $skillDir)

    foreach ($file in $files) {
        $relative = $file.path.Substring($skillPath.Length).TrimStart("/")
        if (-not $relative) { continue }
        $target = Join-Path $skillDir ($relative -replace "/", "\")
        [void](New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target))
        $url = "https://raw.githubusercontent.com/$Repo/$Branch/$($file.path)"
        try {
            $bytes = (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 60).Content
            if ($bytes -is [byte[]]) {
                [IO.File]::WriteAllBytes($target, $bytes)
            }
            else {
                [IO.File]::WriteAllText($target, [string]$bytes, [Text.UTF8Encoding]::new($false))
            }
        }
        catch {
            Write-Warning "  No se pudo descargar $($file.path): $($_.Exception.Message)"
        }
    }
    Write-Host "  [ok]   $skillName -> $skillDir" -ForegroundColor Green
    $installed++
}

Write-Host ""
Write-Host "Instaladas: $installed   Omitidas: $skipped" -ForegroundColor Green
Write-Host "Reinicia Claude Code para que las detecte." -ForegroundColor Cyan
