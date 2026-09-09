param(
  [string]$InputTsv = "narration_segments.tsv",
  [string]$OutDir = "audio",
  [int]$Speaker = 1310138977,
  [string]$Engine = "http://127.0.0.1:10101"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$queryDir = Join-Path $OutDir "queries"
New-Item -ItemType Directory -Force -Path $queryDir | Out-Null

$null = Invoke-RestMethod -Method Post -Uri "$Engine/initialize_speaker?speaker=$Speaker"

$lines = Get-Content -Path $InputTsv -Encoding UTF8
foreach ($line in $lines) {
  if ([string]::IsNullOrWhiteSpace($line)) { continue }
  $parts = $line -split "`t", 4
  if ($parts.Count -lt 2) { continue }

  $id = $parts[0]
  $text = $parts[1]
  if ($id -eq "scene_id") { continue }
  $encodedText = [System.Uri]::EscapeDataString($text)
  $queryFile = Join-Path $queryDir ("scene_{0}.json" -f $id)
  $outFile = Join-Path $OutDir ("scene_{0}.wav" -f $id)

  Invoke-WebRequest -Method Post -Uri "$Engine/audio_query?text=$encodedText&speaker=$Speaker" -OutFile $queryFile
  $query = Get-Content -Path $queryFile -Encoding UTF8 | ConvertFrom-Json
  $query.speedScale = 1.02
  $query.intonationScale = 0.92
  $query.prePhonemeLength = 0.16
  $query.postPhonemeLength = 0.28
  $queryBodyText = $query | ConvertTo-Json -Depth 100
  [System.IO.File]::WriteAllText($queryFile, $queryBodyText, [System.Text.Encoding]::UTF8)
  $queryBody = [System.IO.File]::ReadAllBytes($queryFile)
  Invoke-WebRequest -Method Post -Uri "$Engine/synthesis?speaker=$Speaker" -ContentType "application/json" -Body $queryBody -OutFile $outFile

  if (!(Test-Path $outFile) -or ((Get-Item $outFile).Length -le 44)) {
    throw "Failed to create $outFile"
  }
  Write-Host "created $outFile"
}
