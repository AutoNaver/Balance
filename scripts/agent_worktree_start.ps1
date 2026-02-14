param(
    [Parameter(Mandatory = $true)]
    [string]$Agent,
    [Parameter(Mandatory = $true)]
    [string]$Feature,
    [string]$BaseBranch = "main"
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

$branch = "feature/$Feature"
$worktreesRoot = Join-Path $root "..\agent-worktrees"
$agentRoot = Join-Path $worktreesRoot $Agent
$target = Join-Path $agentRoot $Feature

if (-not (Test-Path $worktreesRoot)) {
    New-Item -ItemType Directory -Path $worktreesRoot | Out-Null
}
if (-not (Test-Path $agentRoot)) {
    New-Item -ItemType Directory -Path $agentRoot | Out-Null
}
if (Test-Path $target) {
    throw "Worktree path already exists: $target"
}

git fetch origin $BaseBranch
git worktree add -b $branch $target "origin/$BaseBranch"

Write-Host "Created worktree: $target"
Write-Host "Branch: $branch"
Write-Host "Next: cd `"$target`""
