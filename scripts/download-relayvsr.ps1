param([string]$ModelDirectory = 'D:\RelayVsrModel')
$ErrorActionPreference = 'Stop'
$revision = '751954dc8adf34aa1d636a39fc548b9089703c85'
$files = @{
    'flash.safetensors' = '7b8b8c99275fd5c4501b0589cc7b4c4506456a5df83160ef4e207e147b30f714'
    'wan.safetensors' = '638acb6a27c17ba87b2e66a1770f17e61a99ad87cfff6fa3d3e05c2d57f2eb98'
}
New-Item -ItemType Directory -Path $ModelDirectory -Force | Out-Null
foreach ($entry in $files.GetEnumerator()) {
    $target = Join-Path $ModelDirectory $entry.Key
    if (Test-Path -LiteralPath $target) {
        if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ieq $entry.Value) {
            Write-Host "$($entry.Key): уже загружен и проверен"
            continue
        }
        throw "Хеш $target не совпадает. Сохраните/переименуйте этот файл перед повторной загрузкой."
    }
    $partial = "$target.part"
    & curl.exe -L --fail --retry 3 -C - --output $partial "https://huggingface.co/kopper/RelayVSR/resolve/$revision/$($entry.Key)"
    if ($LASTEXITCODE -ne 0) { throw "Загрузка не завершена. Повторите скрипт для продолжения." }
    if ((Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash -ine $entry.Value) {
        throw "Хеш $partial не совпадает с официальным файлом. Готовый файл не опубликован."
    }
    Move-Item -LiteralPath $partial -Destination $target
}
