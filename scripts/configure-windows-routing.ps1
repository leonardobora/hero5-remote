<#
.SYNOPSIS
    Configure Windows routing so Ethernet stays as the default internet path
    while the GoPro Wi-Fi network is used only for 10.5.5.9/32.

.DESCRIPTION
    The GoPro Hero 5 Black creates an AP on 10.5.5.0/24. When you connect
    your PC to that Wi-Fi, Windows may try to route all traffic through it
    and you lose internet. This script:

    1. Detects the GoPro Wi-Fi interface (any interface with an IP in 10.5.5.0/24).
    2. Detects the internet interface (Ethernet or another Wi-Fi) that has
       a default gateway outside the GoPro network.
    3. Sets interface metrics so the internet interface wins.
    4. Adds a persistent route for 10.5.5.9/32 through the GoPro interface.
    5. Removes the default gateway from the GoPro interface if it exists.

    Run this as Administrator after connecting to the GoPro Wi-Fi network.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$GoProNetwork = "10.5.5.0/24",
    [string]$GoProHost = "10.5.5.9",
    [int]$InternetMetric = 1,
    [int]$GoProMetric = 50
)

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "[OK]   $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

# Requires elevation.
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warn "This script must run as Administrator. Right-click PowerShell and choose 'Run as administrator'."
    exit 1
}

$goproPrefix = $GoProNetwork.Split('/')[0]
$goproBits = [int]$GoProNetwork.Split('/')[1]

# Build a helper to test if an IP belongs to the GoPro subnet.
function Test-GoProSubnet {
    param([string]$Ip)
    try {
        $addr = [System.Net.IPAddress]::Parse($Ip).GetAddressBytes()
        [Array]::Reverse($addr)
        $ipInt = [BitConverter]::ToUInt32($addr, 0)
        $mask = [uint32]([math]::Pow(2, 32) - [math]::Pow(2, 32 - $goproBits))
        $netBytes = [System.Net.IPAddress]::Parse($goproPrefix).GetAddressBytes()
        [Array]::Reverse($netBytes)
        $netInt = [BitConverter]::ToUInt32($netBytes, 0)
        return ($ipInt -band $mask) -eq ($netInt -band $mask)
    }
    catch {
        return $false
    }
}

# Gather interfaces with IPv4 addresses and default gateways.
$adapters = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' -and $_.InterfaceOperationalStatus -eq 'Up' }
$ipConfigs = Get-NetIPConfiguration | Where-Object { $_.NetAdapter -in $adapters }

$goproInterface = $null
$internetInterface = $null

foreach ($cfg in $ipConfigs) {
    $ipv4 = $cfg.IPv4Address | Select-Object -First 1
    $gateway = $cfg.IPv4DefaultGateway | Select-Object -First 1

    if (-not $ipv4) { continue }

    $ip = $ipv4.IPAddress
    $gw = if ($gateway) { $gateway.NextHop } else { $null }
    $idx = $cfg.InterfaceIndex
    $name = $cfg.NetAdapter.Name

    Write-Info "Found interface '$name' (idx=$idx) with IP=$ip, Gateway=$gw"

    if (Test-GoProSubnet -Ip $ip) {
        $goproInterface = $cfg
        Write-Info " -> Detected as GoPro Wi-Fi interface."
    }
    elseif ($gw -and -not (Test-GoProSubnet -Ip $gw)) {
        $internetInterface = $cfg
        Write-Info " -> Detected as internet interface."
    }
}

if (-not $goproInterface) {
    Write-Warn "No interface found in $GoProNetwork. Make sure you are connected to the GoPro Wi-Fi network."
    exit 2
}

if (-not $internetInterface) {
    Write-Warn "No internet interface found. If you only have one adapter connected, this script is unnecessary."
    exit 3
}

Write-Info "GoPro interface:    $($goproInterface.NetAdapter.Name) (idx=$($goproInterface.InterfaceIndex))"
Write-Info "Internet interface: $($internetInterface.NetAdapter.Name) (idx=$($internetInterface.InterfaceIndex))"

# Set metrics.
if ($PSCmdlet.ShouldProcess($internetInterface.NetAdapter.Name, "Set interface metric to $InternetMetric")) {
    Set-NetIPInterface -InterfaceIndex $internetInterface.InterfaceIndex -InterfaceMetric $InternetMetric -ErrorAction Stop
    Write-Ok "Set '$($internetInterface.NetAdapter.Name)' metric to $InternetMetric (highest priority)."
}

if ($PSCmdlet.ShouldProcess($goproInterface.NetAdapter.Name, "Set interface metric to $GoProMetric")) {
    Set-NetIPInterface -InterfaceIndex $goproInterface.InterfaceIndex -InterfaceMetric $GoProMetric -ErrorAction Stop
    Write-Ok "Set '$($goproInterface.NetAdapter.Name)' metric to $GoProMetric (lowest priority)."
}

# Remove default gateway from GoPro interface if present.
$goproGw = $goproInterface.IPv4DefaultGateway | Select-Object -First 1
if ($goproGw) {
    if ($PSCmdlet.ShouldProcess("$GoProHost via $($goproInterface.NetAdapter.Name)", "Remove default gateway $($goproGw.NextHop)")) {
        Remove-NetRoute -InterfaceIndex $goproInterface.InterfaceIndex -DestinationPrefix "0.0.0.0/0" -NextHop $goproGw.NextHop -Confirm:$false -ErrorAction SilentlyContinue
        Write-Ok "Removed default gateway $($goproGw.NextHop) from GoPro interface."
    }
}

# Add persistent route for the GoPro host through the GoPro interface.
$existingRoute = Get-NetRoute -DestinationPrefix "$GoProHost/32" -ErrorAction SilentlyContinue
if (-not $existingRoute) {
    if ($PSCmdlet.ShouldProcess("$GoProHost/32", "Add persistent route via interface $($goproInterface.InterfaceIndex)")) {
        New-NetRoute -DestinationPrefix "$GoProHost/32" -InterfaceIndex $goproInterface.InterfaceIndex -PolicyStore PersistentStore -ErrorAction Stop | Out-Null
        Write-Ok "Added persistent route $GoProHost/32 through GoPro Wi-Fi interface."
    }
}
else {
    Write-Info "Route $GoProHost/32 already exists."
}

Write-Ok "Routing configured. You should now have internet via Ethernet and GoPro access via Wi-Fi."
Write-Info "Test with: ping $GoProHost"
