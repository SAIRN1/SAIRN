# Item 5: launch the pinned suite DETACHED so a harness stop cannot kill it.
#
# Batch 24's run died twice inside a managed background shell: the shell was
# stopped and the whole process tree went with it, leaving suite.status saying
# RUNNING for a dead pid. Start-Process detaches the child from this shell, so
# killing the shell leaves it alone.
#
# It writes the SAME .status path capture_exit.py always writes, so the liveness
# check and the childwatch are unchanged.

$ErrorActionPreference = 'Stop'
$repo = 'C:\Users\marsh\Documents\SAIRN-cody'
$d    = 'C:\Users\marsh\AppData\Local\Temp\claude\C--Users-marsh-Documents-SAIRN-cody\20e0ab2b-79b3-44cb-b3dc-fe1a01d0c89e\scratchpad\b25\i5'
New-Item -ItemType Directory -Force -Path $d | Out-Null

Set-Location $repo
$sha = (git rev-parse HEAD).Trim()
"SHA $sha"                                        | Out-File -FilePath "$d\meta.txt" -Encoding utf8
"START $((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))" | Out-File -FilePath "$d\meta.txt" -Encoding utf8 -Append
git status --porcelain                            | Out-File -FilePath "$d\git_before.txt" -Encoding utf8
(git config --get core.bare)                      | Out-File -FilePath "$d\corebare_before.txt" -Encoding utf8

$suite = Start-Process -FilePath 'python' `
  -ArgumentList @('tools/capture_exit.py','--status',"$d\suite.status",'--',
                  'python','tools/run_all_tests.py','--pinned','--out',"$d\suite.out") `
  -WorkingDirectory $repo -WindowStyle Hidden -PassThru
"SUITE_PID $($suite.Id)" | Out-File -FilePath "$d\pids.txt" -Encoding utf8

Start-Sleep -Seconds 3

$watch = Start-Process -FilePath 'python' `
  -ArgumentList @("$($d -replace 'i5$','')childwatch.py", "$($suite.Id)",
                  "$d\suite.status", "$d\child_times.txt") `
  -WorkingDirectory $repo -WindowStyle Hidden -PassThru
"WATCH_PID $($watch.Id)" | Out-File -FilePath "$d\pids.txt" -Encoding utf8 -Append

Write-Output "SUITE_PID $($suite.Id)"
Write-Output "WATCH_PID $($watch.Id)"
Write-Output "STATUS    $d\suite.status"
Write-Output "DETACHED  both processes are Start-Process children, not children of this shell"
