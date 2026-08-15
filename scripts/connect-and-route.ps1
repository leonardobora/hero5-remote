<#
.SYNOPSIS
    Connect to a GoPro Wi-Fi network and configure Windows routing so
    Ethernet remains the default internet path.

.DESCRIPTION
    1. Creates/updates a Wi-Fi profile for the GoPro network.
    2. Connects to it.
    3. Waits until the interface gets an IP in 10.5.5.0/24.
    4. Calls configure-windows-routing.ps1 to fix routing.

    Run this as Administrator.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Ssid,

    [Parameter(Mandatory = $true)]
    [string]$Password,

    [string]$GoProHost = "10.5.5.9",
    [int]$InternetMetric = 1,
    [int]$GoProMetric = 50
)

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "[OK]   $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warn "This script must run as Administrator."
    exit 1
}

$profileXml = @"
<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
  <name>$([System.Security.SecurityElement]::Escape($Ssid))</name>
  <SSIDConfig>
    <SSID>
      <name>$([System.Security.SecurityElement]::Escape($Ssid))</name>
    </SSID>
  </SSIDConfig>
  <connectionType>ESS</connectionType>
  <connectionMode>auto</connectionMode>
  <MSM>
    <security>
      <authEncryption>
        <authentication>WPA2PSK</authentication>
        <encryption>AES</encryption>
        <useOneX>false</useOneX>
      </authEncryption>
      <sharedKey>
        <keyType>passPhrase</keyType>
        <protected>false</protected>
        <keyMaterial>$([System.Security.SecurityElement]::Escape($Password))</keyMaterial>
      </sharedKey>
    </security>
  </MSM>
</WLANProfile>
"@

$tempProfile = [System.IO.Path]::GetTempFileName() + ".xml"
$profileXml | Set-Content -Path $tempProfile -Encoding UTF8

Write-Info "Adding Wi-Fi profile for '$Ssid'..."
netsh wlan delete profile name="$Ssid" | Out-Null
$result = netsh wlan add profile filename="$tempProfile" 2>&1
Remove-Item -Path $tempProfile -ErrorAction SilentlyContinue

if ($LASTEXITCODE -ne 0) {
    Write-Warn "Failed to add profile: $result"
    exit 2
}

Write-Info "Connecting to '$Ssid'..."
$result = netsh wlan connect name="$Ssid" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Warn "Failed to connect: $result"
    exit 3
}

# Wait for the interface to get an IP in the GoPro subnet.
Write-Info "Waiting for GoPro IP (10.5.5.x)..."
$connected = $false
for ($i = 0; $i -lt 30; $i++) {
    $cfg = Get-NetIPConfiguration | Where-Object {
        $_.IPv4Address.IPAddress -like "10.5.5.*"
    } | Select-Object -First 1

    if ($cfg) {
        Write-Ok "Connected via interface '$($cfg.NetAdapter.Name)' with IP $($cfg.IPv4Address.IPAddress)"
        $connected = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $connected) {
    Write-Warn "Could not obtain IP from GoPro network. Check signal and password."
    exit 4
}

# Complete pairing so the camera leaves the Connect screen.
$pairUrl = "http://$GoProHost/gp/gpControl/command/wireless/pair/complete?success=1&deviceName=DESKTOP"
Write-Info "Completing GoPro pairing via $pairUrl ..."
try {
    $response = Invoke-WebRequest -Uri $pairUrl -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
    Write-Ok "Pairing response: $($response.StatusCode)"
}
catch {
    Write-Warn "Pairing call failed: $_"
    Write-Warn "You may need to retry or complete pairing manually via the GoPro app once."
}

Start-Sleep -Seconds 2

# Now run the routing configuration.
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$routingScript = Join-Path $scriptDir "configure-windows-routing.ps1"
& $routingScript -GoProHost $GoProHost -InternetMetric $InternetMetric -GoProMetric $GoProMetric

Write-Info "Press Enter to close this window."
Read-Host
