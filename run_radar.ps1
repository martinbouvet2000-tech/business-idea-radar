# Reddit Idea Radar — One-command runner (FREE mode)
# Usage: .\run_radar.ps1
# Uses Claude Code CLI subscription — zero API credits needed

$ErrorActionPreference = "Stop"
$script = Join-Path $PSScriptRoot "reddit_idea_radar.py"

Write-Host "`n[RADAR] Starting full scan (FREE mode)..." -ForegroundColor Cyan

# Step 1: Scrape Reddit
python $script --scrape-only --hours 48

# Step 2: Find latest threads file
$latest = Get-ChildItem "$env:USERPROFILE\idea-radar-output\THREADS_*.json" |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1

if (-not $latest) {
    Write-Host "[!] No threads file found" -ForegroundColor Red
    exit 1
}

Write-Host "`n[RADAR] Analyzing with Claude Code CLI..." -ForegroundColor Cyan

# Step 3: Analyze with local Claude Code CLI
python $script --from-file $latest.FullName --local

Write-Host "`n[RADAR] Done! Output: $env:USERPROFILE\idea-radar-output\" -ForegroundColor Green
