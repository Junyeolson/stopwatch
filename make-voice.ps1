# Generates Korean narration with the built-in Windows voice (Microsoft Heami)
# and embeds it into shorts.html (built from template.html).
param([int]$Rate = 2)

$ErrorActionPreference = 'Stop'
$dir = $PSScriptRoot
Add-Type -AssemblyName System.Speech

$script = Get-Content (Join-Path $dir 'script.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(24000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$tmp = Join-Path $env:TEMP 'ai-jobs-voice'
New-Item -ItemType Directory -Force $tmp | Out-Null

$out = @()
foreach ($seg in $script) {
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $synth.SelectVoice('Microsoft Heami Desktop')
    $synth.Rate = $Rate
    $wav = Join-Path $tmp ($seg.id + '.wav')
    $synth.SetOutputToWaveFile($wav, $fmt)
    $synth.Speak($seg.say)
    $synth.Dispose()
    $bytes = [IO.File]::ReadAllBytes($wav)
    $dur = ($bytes.Length - 44) / (24000 * 2)
    $out += [pscustomobject]@{ id = $seg.id; dur = [math]::Round($dur, 3); b64 = [Convert]::ToBase64String($bytes) }
    Write-Host ("{0,-6} {1,6:N2}s  {2}" -f $seg.id, $dur, $seg.say)
}
$total = ($out | Measure-Object dur -Sum).Sum
Write-Host ("speech total: {0:N2}s" -f $total)

$json = $out | ConvertTo-Json -Compress
$tplPath = Join-Path $dir 'template.html'
if (Test-Path $tplPath) {
    $tpl = Get-Content $tplPath -Raw -Encoding UTF8
    $html = $tpl.Replace('/*VOICE_DATA*/[]', $json)
    [IO.File]::WriteAllText((Join-Path $dir 'shorts.html'), $html, (New-Object Text.UTF8Encoding($false)))
    Write-Host 'wrote shorts.html'
}
