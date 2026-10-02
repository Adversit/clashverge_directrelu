param([ValidateSet('start', 'restart', 'stop')][string]$Action = 'start')
$ErrorActionPreference = 'Stop'
try {
$taskRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonLocal = Join-Path $taskRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $pythonLocal)) {
    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if (!$pythonCommand) { throw 'Install Python 3.10+ and Node.js, then retry.' }
    $pythonLocal = $pythonCommand.Source
}
$taskLauncher = Start-Process -FilePath $pythonLocal -ArgumentList @(('"' + (Join-Path $taskRoot 'launcher.py') + '"'), '--action', $Action) -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru
$taskLauncher.WaitForExit()
exit $taskLauncher.ExitCode
} catch {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'Clash Direct Manager') | Out-Null
    exit 1
}
