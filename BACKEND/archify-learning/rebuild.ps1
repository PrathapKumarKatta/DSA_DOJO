$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    $run = [DateTime]::Now.ToString('yyyyMMdd-HHmmss-fff')
    $items = @(
        @{Slug='01-taskflow-map'; Type='architecture'},
        @{Slug='02-task-edit'; Type='sequence'},
        @{Slug='03-reminders'; Type='architecture'},
        @{Slug='04-how-archify-works'; Type='architecture'}
    )
    foreach ($item in $items) {
        $cliArgs = @(
            'archify/archify/bin/archify.mjs', 'finalize', $item.Type,
            "archify-learning/sources/$($item.Slug).json",
            "archify-learning/diagrams/$($item.Slug).html",
            '--quality', 'showcase', '--out-dir',
            "archify-learning/reviews/$run/$($item.Slug)", '--json'
        )
        if ($item.Slug -eq '04-how-archify-works') { $cliArgs += @('--repo-root', 'archify') }
        & node @cliArgs
        if ($LASTEXITCODE -ne 0) { throw "Diagram delivery failed for $($item.Slug). Read the diagnostic above." }
    }
} finally { Pop-Location }
