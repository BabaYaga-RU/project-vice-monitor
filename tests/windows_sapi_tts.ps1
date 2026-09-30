# Local-only adapter so the renderer can be exercised with Windows speech.
# GitHub Actions uses espeak-ng; this file is only a test command shim.
$allArgs = @($args)
$output = $null
$speechParts = @()
for ($i = 0; $i -lt $allArgs.Count; $i++) {
    $value = [string]$allArgs[$i]
    if ($value -in @('-v', '-s', '-w')) {
        if ($value -eq '-w' -and $i + 1 -lt $allArgs.Count) { $output = [string]$allArgs[$i + 1] }
        $i++
        continue
    }
    if (-not $value.StartsWith('-')) { $speechParts += $value }
}
if (-not $output) { throw 'Missing WAV destination.' }
Add-Type -AssemblyName System.Speech
$speaker = [System.Speech.Synthesis.SpeechSynthesizer]::new()
$speaker.Rate = -1
$speaker.SetOutputToWaveFile($output, [System.Speech.AudioFormat.SpeechAudioFormatInfo]::new(22050, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono))
$speaker.Speak(($speechParts -join ' '))
$speaker.Dispose()
