# Print the current IPv4 source address for the home network.
$ErrorActionPreference = 'Stop'

$connected = @(Get-NetIPInterface -AddressFamily IPv4 -ConnectionState Connected |
    ForEach-Object InterfaceIndex)
$routes = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' |
    Where-Object { $connected -contains $_.InterfaceIndex } |
    Sort-Object { $_.RouteMetric + $_.InterfaceMetric }

foreach ($route in $routes) {
    $destination = $route.NextHop
    if ($destination -eq '0.0.0.0') {
        $destination = '1.1.1.1'
    }

    # Ask Windows which source address it would use on this interface. This sends no traffic.
    $address = Find-NetRoute -RemoteIPAddress $destination -InterfaceIndex $route.InterfaceIndex -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -and $_.AddressState -eq 'Preferred' -and -not $_.SkipAsSource -and
            $_.IPAddress -notmatch '^(127\.|169\.254\.)'
        } |
        Select-Object -First 1
    if ($address) {
        $address.IPAddress
        return
    }
}
