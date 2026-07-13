param(
    [Parameter(Mandatory = $true)][string]$InputTextFile,
    [Parameter(Mandatory = $true)][string]$OutputWaveFile,
    [Parameter(Mandatory = $true)][ValidateSet('Microsoft Huihui Desktop')][string]$Voice,
    [Parameter(Mandatory = $true)][ValidateRange(-10, 10)][int]$Rate
)

$ErrorActionPreference = 'Stop'
$text = [System.IO.File]::ReadAllText($InputTextFile, [System.Text.UTF8Encoding]::new($false))
if ([string]::IsNullOrWhiteSpace($text)) { throw 'tts_empty_input' }
Add-Type -AssemblyName System.Speech
$speaker = [System.Speech.Synthesis.SpeechSynthesizer]::new()
try {
    $speaker.SelectVoice($Voice)
    $speaker.Rate = $Rate
    $speaker.SetOutputToWaveFile($OutputWaveFile)
    $speaker.Speak($text)
} finally {
    $speaker.Dispose()
}
