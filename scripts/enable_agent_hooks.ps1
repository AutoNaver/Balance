param()

$ErrorActionPreference = "Stop"

$root = (git rev-parse --show-toplevel).Trim()
Set-Location $root

git config core.hooksPath ".githooks"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to set core.hooksPath."
}

Write-Host "Enabled repository hooks at .githooks"
Write-Host "Active pre-push rule: only pushes to refs/heads/main are allowed."
