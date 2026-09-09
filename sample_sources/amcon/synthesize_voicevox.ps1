param(
  [Parameter(Mandatory = $true)][string]$InputTsv,
  [Parameter(Mandatory = $true)][string]$OutDir,
  [int]$Speaker = 3
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$engine = "http://127.0.0.1:50021"
$lines = Get-Content -Path $InputTsv -Encoding UTF8

foreach ($line in $lines) {
  if ([string]::IsNullOrWhiteSpace($line)) { continue }
  $parts = $line -split "`t", 2
  if ($parts.Count -lt 2) { continue }

  $id = $parts[0]
  $text = $parts[1]
  $encodedText = [System.Uri]::EscapeDataString($text)

  $query = Invoke-RestMethod -Method Post -Uri "$engine/audio_query?text=$encodedText&speaker=$Speaker"
  $query.speedScale = 1.08
  $query.pitchScale = 0.02
  $query.intonationScale = 1.05
  $query.prePhonemeLength = 0.18
  $query.postPhonemeLength = 0.28

  $body = $query | ConvertTo-Json -Depth 100
  $outFile = Join-Path $OutDir ("scene_{0}.wav" -f $id)
  Invoke-WebRequest -Method Post -Uri "$engine/synthesis?speaker=$Speaker" -ContentType "application/json" -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -OutFile $outFile
  Write-Host "created $outFile"
}
