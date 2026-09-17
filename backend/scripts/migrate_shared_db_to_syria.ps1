# Copy legacy shared `eduspark` database into dedicated `eduspark_syria` (Windows / local dev).
# Preserves all rows; run once after setup_syria_db.sql if you were on the shared DB.
#
# Usage (from project root, adjust host/user/password):
#   .\backend\scripts\migrate_shared_db_to_syria.ps1

$ErrorActionPreference = "Stop"
$pgHost = $env:POSTGRES_HOST
if (-not $pgHost) { $pgHost = "localhost" }
$pgPort = $env:POSTGRES_PORT
if (-not $pgPort) { $pgPort = "5432" }
$pgUser = $env:POSTGRES_USER
if (-not $pgUser) { $pgUser = "postgres" }

$sourceDb = "eduspark"
$targetDb = "eduspark_syria"
$dumpFile = Join-Path $env:TEMP "eduspark_syria_migrate.dump"

Write-Host "Dumping $sourceDb from ${pgHost}:${pgPort} ..."
& pg_dump -h $pgHost -p $pgPort -U $pgUser -Fc -f $dumpFile $sourceDb

Write-Host "Restoring into $targetDb ..."
& pg_restore -h $pgHost -p $pgPort -U $pgUser -d $targetDb --clean --if-exists $dumpFile

Write-Host "Done. Set POSTGRES_DB=eduspark_syria in .env and restart the backend."
