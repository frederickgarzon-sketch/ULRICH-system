$ErrorActionPreference = "Stop"
$BaseUrl = if ($args.Count -gt 0) { $args[0].TrimEnd('/') } else { "http://127.0.0.1:8000" }
Write-Host "Behavioral Monitoring Hardware Validation"
Write-Host "Server: $BaseUrl"
$health = Invoke-RestMethod "$BaseUrl/api/health"
$report = Invoke-RestMethod "$BaseUrl/api/hardware/validation"
$system = Invoke-RestMethod "$BaseUrl/api/system/status"
$report | ConvertTo-Json -Depth 8
Write-Host ""
Write-Host "Result: $($report.passed)/$($report.total) automatic checks passed"
Write-Host "AI device: $($system.ai_device)"
Write-Host "Raw recording: $($system.raw_video_recording)"
if (-not $report.ready) { exit 2 }

