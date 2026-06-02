# BRK File Association Installer for Windows
# Run as Administrator
#
# BRK is NOT a universal lossless compressor.
# BRK does not break Shannon's theorem.
#
# Usage: powershell -ExecutionPolicy Bypass -File install-association.ps1

param(
    [switch]$Uninstall = $false
)

$ErrorActionPreference = "Stop"

$ProgId = "BRK.Container"
$Extension = ".brk"
$MimeType = "application/vnd.brk"
$BrkCommand = Get-Command brk -ErrorAction SilentlyContinue

function Write-Status($msg) {
    Write-Host "[BRK] $msg" -ForegroundColor Cyan
}

if ($Uninstall) {
    Write-Status "Uninstalling BRK file association..."
    try {
        Remove-Item -Path "HKCU:\Software\Classes\$Extension" -Force -Recurse -ErrorAction SilentlyContinue
        Remove-Item -Path "HKCU:\Software\Classes\$ProgId" -Force -Recurse -ErrorAction SilentlyContinue
        Write-Status "File association removed successfully."
    } catch {
        Write-Status "Failed to remove some registry entries: $_"
    }
    exit 0
}

# Check if brk is available
if (-not $BrkCommand) {
    Write-Status "WARNING: 'brk' command not found in PATH."
    Write-Status "Install with: pip install -e ."
    Write-Status "Continuing anyway..."
    $BrkPath = "brk"
} else {
    $BrkPath = $BrkCommand.Source
    Write-Status "Found brk at: $BrkPath"
}

Write-Status "Registering .$Extension file extension..."

# Register .brk extension
New-Item -Path "HKCU:\Software\Classes\$Extension" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\$Extension" -Name "(Default)" -Value $ProgId
Set-ItemProperty -Path "HKCU:\Software\Classes\$Extension" -Name "Content Type" -Value $MimeType
Set-ItemProperty -Path "HKCU:\Software\Classes\$Extension" -Name "PerceivedType" -Value "Compressed"

# Register ProgID
New-Item -Path "HKCU:\Software\Classes\$ProgId" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\$ProgId" -Name "(Default)" -Value "BRK Breakthrough Container"

# DefaultIcon
New-Item -Path "HKCU:\Software\Classes\$ProgId\DefaultIcon" -Force | Out-Null

# Shell commands
New-Item -Path "HKCU:\Software\Classes\$ProgId\shell" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\$ProgId\shell" -Name "(Default)" -Value "inspect"

# Inspect (default double-click)
New-Item -Path "HKCU:\Software\Classes\$ProgId\shell\inspect" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\$ProgId\shell\inspect" -Name "(Default)" -Value "&Inspect BRK Container"
New-Item -Path "HKCU:\Software\Classes\$ProgId\shell\inspect\command" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\$ProgId\shell\inspect\command" -Name "(Default)" -Value "cmd.exe /c `"brk inspect `"%1`" & pause`""

# Verify
New-Item -Path "HKCU:\Software\Classes\$ProgId\shell\verify" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\$ProgId\shell\verify" -Name "(Default)" -Value "&Verify BRK Container"
New-Item -Path "HKCU:\Software\Classes\$ProgId\shell\verify\command" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\$ProgId\shell\verify\command" -Name "(Default)" -Value "cmd.exe /c `"brk verify `"%1`" & pause`""

# Decompress
New-Item -Path "HKCU:\Software\Classes\$ProgId\shell\decompress" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\$ProgId\shell\decompress" -Name "(Default)" -Value "&Reconstruct CSV from BRK..."
New-Item -Path "HKCU:\Software\Classes\$ProgId\shell\decompress\command" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\$ProgId\shell\decompress\command" -Name "(Default)" -Value "cmd.exe /c `"brk decompress-sensor `"%1`" `"%1.reconstructed.csv`" --step-minutes 60 & echo Reconstructed: %1.reconstructed.csv & pause`""

Write-Status ""
Write-Status "Registration complete!"
Write-Status ""
Write-Status "  Extension : .$Extension"
Write-Status "  MIME type : $MimeType"
Write-Status "  ProgID    : $ProgId"
Write-Status ""
Write-Status "  Double-click .brk file  -> Inspect"
Write-Status "  Right-click .brk file   -> Verify / Reconstruct CSV"
Write-Status ""
Write-Status "  To uninstall: powershell -File install-association.ps1 -Uninstall"
