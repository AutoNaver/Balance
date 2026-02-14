param(
    [Parameter(Mandatory = $true)]
    [string]$CommitMessage,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

$root = (git rev-parse --show-toplevel).Trim()
Set-Location $root

$branch = (git branch --show-current).Trim()
if (-not $branch) {
    throw "Not on a branch."
}
if ($branch -eq "main") {
    throw "Do not complete features from main. Use a feature branch worktree."
}

git add -A
if ($LASTEXITCODE -ne 0) {
    throw "git add failed."
}

$staged = git diff --cached --name-only
if (-not $staged) {
    throw "No staged changes to commit."
}

git commit -m $CommitMessage
if ($LASTEXITCODE -ne 0) {
    throw "git commit failed."
}

if ($SkipTests) {
    pwsh "$PSScriptRoot/agent_publish_feature.ps1" -SkipTests
} else {
    pwsh "$PSScriptRoot/agent_publish_feature.ps1"
}
