[CmdletBinding()]
param(
    [string]$SecretKey,
    [string]$Algorithm,
    [string]$AccessExpireMinutes,
    [string]$OidcSecretKey,
    [string]$OidcAlgorithm,
    [string]$OidcExpireMinutes,
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"

function Set-ProcessEnvironment {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Value
    )

    if ($Value -ne $null -and $Value -ne "") {
        Set-Item -Path "Env:$Name" -Value $Value
    }
}

function Parse-DotEnvLine {
    param([string]$Line)

    $trimmed = $Line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith('#')) {
        return $null
    }

    $parts = $trimmed -split '=', 2
    if ($parts.Count -lt 2) {
        return $null
    }

    $name = $parts[0].Trim()
    $value = $parts[1].Trim()

    if ($value.StartsWith('"') -and $value.EndsWith('"') -and $value.Length -ge 2) {
        $value = $value.Substring(1, $value.Length - 2)
    } elseif ($value.StartsWith("'") -and $value.EndsWith("'") -and $value.Length -ge 2) {
        $value = $value.Substring(1, $value.Length - 2)
    } else {
        $value = ($value -split '\s+#', 2)[0].Trim()
    }

    if (-not $name) {
        return $null
    }

    return @{ Name = $name; Value = $value }
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptRoot '..' '..')
Set-Location $projectRoot

$envFilePath = Join-Path $projectRoot $EnvFile
if (Test-Path $envFilePath) {
    Write-Host "Loading environment variables from $EnvFile"
    foreach ($line in Get-Content -Path $envFilePath) {
        $entry = Parse-DotEnvLine -Line $line
        if ($null -ne $entry) {
            Set-ProcessEnvironment -Name $entry.Name -Value $entry.Value
        }
    }
}

$overrides = @{
    DOCREVIEW360_SECRET_KEY          = $SecretKey
    DOCREVIEW360_ALGORITHM           = $Algorithm
    DOCREVIEW360_ACCESS_EXPIRE_MINUTES = $AccessExpireMinutes
    DOCREVIEW360_OIDC_SECRET_KEY     = $OidcSecretKey
    DOCREVIEW360_OIDC_ALGORITHM      = $OidcAlgorithm
    DOCREVIEW360_OIDC_EXPIRE_MINUTES = $OidcExpireMinutes
}

foreach ($entry in $overrides.GetEnumerator()) {
    if ($null -ne $entry.Value -and $entry.Value -ne "") {
        Set-ProcessEnvironment -Name $entry.Key -Value $entry.Value
    }
}

$defaults = @{
    DOCREVIEW360_SECRET_KEY            = 'docreview360-dev-secret'
    DOCREVIEW360_ALGORITHM             = 'HS256'
    DOCREVIEW360_ACCESS_EXPIRE_MINUTES = '30'
    DOCREVIEW360_OIDC_SECRET_KEY       = 'docreview360-oidc-dev-secret'
    DOCREVIEW360_OIDC_ALGORITHM        = 'HS256'
    DOCREVIEW360_OIDC_EXPIRE_MINUTES   = '30'
}

foreach ($entry in $defaults.GetEnumerator()) {
    $current = (Get-Item -Path "Env:$($entry.Key)" -ErrorAction SilentlyContinue)
    if ($null -eq $current -or [string]::IsNullOrEmpty($current.Value)) {
        Set-ProcessEnvironment -Name $entry.Key -Value $entry.Value
    }
}

$srcPath = Join-Path $projectRoot 'src'
if (-not (Test-Path $srcPath)) {
    throw "Could not locate src directory at $srcPath"
}

if ($env:PYTHONPATH) {
    $paths = $env:PYTHONPATH -split ';'
    if ($paths -notcontains $srcPath) {
        $env:PYTHONPATH = "$srcPath;" + $env:PYTHONPATH
    }
} else {
    $env:PYTHONPATH = $srcPath
}
Set-ProcessEnvironment -Name 'PYTHONPATH' -Value $env:PYTHONPATH

$venvPython = [System.IO.Path]::Combine($projectRoot, '.venv', 'Scripts', 'python.exe')
if (-not (Test-Path $venvPython)) {
    $fallbackPython = [System.IO.Path]::Combine($projectRoot, '.venv', 'bin', 'python')
    if (Test-Path $fallbackPython) {
        $venvPython = $fallbackPython
    } else {
        throw "Unable to find Python interpreter. Expected $venvPython"
    }
}

Write-Host "Starting DocReview360 backend with $venvPython" -ForegroundColor Green
& $venvPython -m uvicorn docreview360.api:app --reload
