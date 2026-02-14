param(
    [Parameter(Mandatory = $true)]
    [string]$WorktreePath
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $WorktreePath)) {
    throw "Worktree path does not exist: $WorktreePath"
}

git worktree remove "$WorktreePath"
if ($LASTEXITCODE -ne 0) {
    throw "git worktree remove failed."
}

Write-Host "Removed worktree: $WorktreePath"
