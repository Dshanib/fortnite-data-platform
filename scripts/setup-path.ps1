# Optional: run once in PowerShell to prefer installed Python 3.14 over Windows Store aliases.
$pythonRoot = "$env:LOCALAPPDATA\Programs\Python\Python314"
$scripts = "$pythonRoot\Scripts"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$toAdd = @($pythonRoot, $scripts) | Where-Object { $userPath -notlike "*$_*" }
if ($toAdd.Count -gt 0) {
    [Environment]::SetEnvironmentVariable("Path", ($toAdd -join ";") + ";" + $userPath, "User")
    Write-Host "Added Python 3.14 to user PATH. Restart the terminal."
} else {
    Write-Host "Python 3.14 already on user PATH."
}
Write-Host "Also disable Store aliases: Settings > Apps > App execution aliases > turn off python.exe / python3.exe"
