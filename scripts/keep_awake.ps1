# Actively prevent system + display sleep for the duration of the sweep.
# powercfg idle-timeouts do NOT stop a Modern-Standby (S0) laptop from sleeping;
# SetThreadExecutionState with ES_CONTINUOUS does, for as long as this process
# lives. Kill this process (or let the session end) to release the assertion.
$sig = @'
[DllImport("kernel32.dll", SetLastError = true)]
public static extern uint SetThreadExecutionState(uint esFlags);
'@
$k = Add-Type -MemberDefinition $sig -Name Power -Namespace KeepAwake -PassThru
# ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED | ES_AWAYMODE_REQUIRED
$flags = [uint32]0x80000000 -bor 0x00000001 -bor 0x00000002 -bor 0x00000040
Write-Output "keep_awake: asserting ES_CONTINUOUS|SYSTEM|DISPLAY|AWAYMODE $(Get-Date -Format 'HH:mm:ss')"
while ($true) {
    $r = $k::SetThreadExecutionState($flags)
    if ($r -eq 0) { Write-Output "keep_awake: SetThreadExecutionState FAILED $(Get-Date -Format 'HH:mm:ss')" }
    Start-Sleep -Seconds 30
}
