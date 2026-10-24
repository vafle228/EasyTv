# Finds DLNA media renderers (TVs) from the host and prints their description URLs, one per line.
# run.sh passes them to the container, because multicast discovery doesn't work from inside Docker.
param([int]$Seconds = 4)

$targets = 'urn:schemas-upnp-org:device:MediaRenderer:1', 'urn:schemas-upnp-org:service:AVTransport:1'
$up = @(Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object Status -eq 'Up' | ForEach-Object ifIndex)
$locals = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object {
    $_.IPAddress -notmatch '^(127\.|169\.254\.)' -and ($up.Count -eq 0 -or $up -contains $_.InterfaceIndex)
} | ForEach-Object IPAddress)

$socks = @()
foreach ($ip in $locals) {
    try {
        $udp = New-Object Net.Sockets.UdpClient
        $udp.Client.Bind((New-Object Net.IPEndPoint([Net.IPAddress]::Parse($ip), 0)))
        foreach ($st in $targets) {
            $msg = [Text.Encoding]::ASCII.GetBytes("M-SEARCH * HTTP/1.1`r`nHOST: 239.255.255.250:1900`r`nMAN: `"ssdp:discover`"`r`nMX: 2`r`nST: $st`r`n`r`n")
            1..2 | ForEach-Object { [void]$udp.Send($msg, $msg.Length, '239.255.255.250', 1900) }
        }
        $socks += $udp
    } catch {}
}

$found = New-Object 'System.Collections.Generic.HashSet[string]'
$deadline = (Get-Date).AddSeconds($Seconds)
while ((Get-Date) -lt $deadline) {
    foreach ($udp in $socks) {
        while ($udp.Available -gt 0) {
            $ep = New-Object Net.IPEndPoint([Net.IPAddress]::Any, 0)
            try { $text = [Text.Encoding]::ASCII.GetString($udp.Receive([ref]$ep)) } catch { continue }
            if ($text -match '(?im)^LOCATION:\s*(\S+)') { [void]$found.Add($matches[1]) }
        }
    }
    Start-Sleep -Milliseconds 100
}
$socks | ForEach-Object { $_.Close() }
$found | Sort-Object
