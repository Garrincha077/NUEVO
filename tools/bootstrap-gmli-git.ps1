# GMLI — safe one-time Git migration
# Moves ONLY $HOME\gmli-fred-dashboard into its isolated Git repo and connects the already-linked Vercel project.
# It refuses to run against Macro Cockpit or the wrong Vercel project.

$ErrorActionPreference = "Stop"
$Project = Join-Path $HOME "gmli-fred-dashboard"
$ExpectedProjectId = "prj_Q1wLBL4qYx7KkJzhr24xeGAl0X3m"
$ExpectedOrgId = "team_JWLznbfg7CaiWzanxHONivzH"
$Remote = "https://github.com/Garrincha077/NUEVO.git"
$Production = "https://gmli-fred-dashboard.vercel.app"

if (-not (Test-Path $Project)) { throw "GMLI folder not found: $Project" }
if ($Project -match "makro-cockpit") { throw "SAFETY STOP: Macro Cockpit path detected." }
Set-Location $Project

if (-not (Test-Path ".vercel\project.json")) { throw "Missing .vercel/project.json — refusing to guess project identity." }
$v = Get-Content ".vercel\project.json" -Raw | ConvertFrom-Json
if ($v.projectId -ne $ExpectedProjectId -or $v.orgId -ne $ExpectedOrgId) {
  throw "SAFETY STOP: this folder is not the expected gmli-fred-dashboard Vercel project."
}

$required = @("index.html", "api", "lib")
foreach ($r in $required) { if (-not (Test-Path $r)) { throw "SAFETY STOP: expected GMLI source item missing: $r" } }

$beforeStatus = Invoke-RestMethod "$Production/api/status"
$beforeDecision = Invoke-RestMethod "$Production/api/decision"
Write-Host ("Pre-check OK. Core date: " + $beforeDecision.freshness.core_money)

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backup = Join-Path $HOME "gmli-fred-dashboard-pre-git-$stamp.zip"
$items = Get-ChildItem -Force | Where-Object {
  $_.Name -notin @(".git", ".vercel", "node_modules") -and $_.Name -notlike "backup-*"
}
Compress-Archive -Path $items.FullName -DestinationPath $backup -Force
Write-Host "Backup created: $backup"

if (Test-Path ".git") {
  $existing = (git remote get-url origin 2>$null)
  if ($existing -match "makro-cockpit") { throw "SAFETY STOP: Macro Cockpit git remote detected." }
}

$gitignore = @'
.vercel/
node_modules/
backup-*/
.env
.env.local
.env.production
.env.development
.env.*.local
!.env.example
.DS_Store
'@
Set-Content -Path ".gitignore" -Value $gitignore -Encoding UTF8

if (-not (Test-Path ".git")) {
  git init -b main
} else {
  git checkout -B main
}

if (-not (git config user.email)) { git config user.email "gmli-local@users.noreply.github.com" }
if (-not (git config user.name)) { git config user.name "GMLI Local Migration" }

if ((git remote) -contains "origin") { git remote set-url origin $Remote } else { git remote add origin $Remote }

git fetch origin main
$remoteReadme = git show origin/main:README.md 2>$null
if ($LASTEXITCODE -eq 0 -and ($remoteReadme.Trim() -ne "# NUEVO")) {
  throw "SAFETY STOP: remote main is no longer the untouched placeholder. Refusing to overwrite it."
}

git add -A
if (-not (git diff --cached --quiet)) {
  git commit -m "Import current gmli-fred-dashboard production source"
}

git push --force-with-lease origin HEAD:main

npx vercel git connect --yes
npx vercel git ls

$afterStatus = Invoke-RestMethod "$Production/api/status"
$afterDecision = Invoke-RestMethod "$Production/api/decision"
if (-not $afterStatus -or -not $afterDecision) { throw "Post-connect endpoint verification failed." }

Write-Host ""
Write-Host "SUCCESS: GMLI source is now mirrored to isolated Git and Vercel is Git-connected."
Write-Host "Macro Cockpit was not touched."
Write-Host ("Production Core date remains: " + $afterDecision.freshness.core_money)
Write-Host "Next safe step: apply the live-freshness patch as a normal Git commit, then let Vercel deploy from Git."
