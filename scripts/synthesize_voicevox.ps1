param(
  [string]$InputTsv = "narration_segments.tsv",
  [string]$OutDir = "audio",
  [int]$Speaker = 3,
  [string]$Engine = "http://127.0.0.1:50021"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$queryDir = Join-Path $OutDir "queries"
New-Item -ItemType Directory -Force -Path $queryDir | Out-Null

$lines = Get-Content -Path $InputTsv -Encoding UTF8
foreach ($line in $lines) {
  if ([string]::IsNullOrWhiteSpace($line)) { continue }
  $parts = $line -split "`t", 4
  if ($parts.Count -lt 2) { continue }

  $id = $parts[0]
  $text = $parts[1]
  $encodedText = [System.Uri]::EscapeDataString($text)
  $queryFile = Join-Path $queryDir ("scene_{0}.json" -f $id)
  $outFile = Join-Path $OutDir ("scene_{0}.wav" -f $id)

  Invoke-WebRequest -Method Post -Uri "$Engine/audio_query?text=$encodedText&speaker=$Speaker" -OutFile $queryFile
  $query = Get-Content -Path $queryFile -Encoding UTF8 | ConvertFrom-Json
  $query.speedScale = 1.05
  $query.intonationScale = 1.0
  $query.prePhonemeLength = 0.08
  $query.postPhonemeLength = 0.18
  $queryBodyText = $query | ConvertTo-Json -Depth 100
  [System.IO.File]::WriteAllText($queryFile, $queryBodyText, [System.Text.Encoding]::UTF8)
  $queryBody = [System.IO.File]::ReadAllBytes($queryFile)
  Invoke-WebRequest -Method Post -Uri "$Engine/synthesis?speaker=$Speaker" -ContentType "application/json" -Body $queryBody -OutFile $outFile
  Write-Host "created $outFile"
}
