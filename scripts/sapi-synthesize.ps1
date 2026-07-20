param(
    [ValidateSet('Microsoft Huihui Desktop')]
    [string]$Voice,
    [ValidateRange(-10, 10)]
    [int]$Rate
)

$ErrorActionPreference = 'Stop'

# The parent owns the only text boundary.  This repository-owned script accepts
# UTF-8 on standard input and writes exactly one WAV stream to standard output;
# it never receives a caller filename and never creates a temporary file.
$inputStream = [Console]::OpenStandardInput()
$inputBuffer = New-Object System.IO.MemoryStream
$inputStream.CopyTo($inputBuffer)
if ($inputBuffer.Length -le 0 -or $inputBuffer.Length -gt 16384) { exit 2 }
$text = [System.Text.Encoding]::UTF8.GetString($inputBuffer.ToArray())
if ([String]::IsNullOrWhiteSpace($text)) { exit 2 }

Add-Type -AssemblyName System.Speech
$synthesizer = New-Object System.Speech.Synthesis.SpeechSynthesizer
$waveStream = New-Object System.IO.MemoryStream
try {
    $synthesizer.SelectVoice($Voice)
    $synthesizer.Rate = $Rate
    $synthesizer.SetOutputToWaveStream($waveStream)
    $synthesizer.Speak($text)
    if ($waveStream.Length -le 0) { exit 2 }
    $outputStream = [Console]::OpenStandardOutput()
    $bytes = $waveStream.ToArray()
    $outputStream.Write($bytes, 0, $bytes.Length)
    $outputStream.Flush()
}
finally {
    $synthesizer.Dispose()
    $waveStream.Dispose()
    $inputBuffer.Dispose()
}
