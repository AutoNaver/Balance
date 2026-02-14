param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

function Ensure-Success {
    param([int]$Code, [string]$Step)
    if ($Code -ne 0) {
        throw "Failed at step: $Step"
    }
}

$root = (git rev-parse --show-toplevel).Trim()
Set-Location $root

$branch = (git branch --show-current).Trim()
if (-not $branch) {
    throw "Not on a branch."
}
if ($branch -eq "main") {
    throw "Do not develop on main. Use a feature branch in a dedicated worktree."
}

$status = git status --porcelain
if ($status) {
    throw "Working tree is not clean. Commit/stash changes before publish."
}

if (-not $SkipTests) {
    python -m pytest -q
    Ensure-Success $LASTEXITCODE "pytest"
}

git fetch origin main
Ensure-Success $LASTEXITCODE "git fetch origin main"

$local = (git rev-parse HEAD).Trim()
$remoteMain = (git rev-parse origin/main).Trim()
$base = (git merge-base HEAD origin/main).Trim()

if ($base -ne $remoteMain) {
    throw "HEAD is not a fast-forward of origin/main. Rebase on origin/main and retry."
}

git push origin HEAD:main
Ensure-Success $LASTEXITCODE "git push origin HEAD:main"

Write-Host "Published feature branch '$branch' to origin/main (fast-forward)."
