@echo off
title Cosys-AirSim Keyboard Flight (one-click)

rem 1) Always start a FRESH Blocks instance:
rem    - kill any zombie/leftover instance first (a windowless instance can
rem      still hold the RPC port, which makes "ready" checks lie)
rem    - UE packaged exe must be started with its own folder as working dir
powershell -NoProfile -Command "Stop-Process -Name Blocks -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 2; Start-Process 'E:\drone-sim\platforms\cosys-airsim\env\Windows\Blocks.exe' -WorkingDirectory 'E:\drone-sim\platforms\cosys-airsim\env\Windows'"

rem 2) Ready = the actual WINDOW is up (MainWindowHandle != 0) AND RPC port answers.
rem    First launch / shader recompilation can take several minutes - do not kill
rem    the process while CPU is busy, or shader compilation restarts next time.
echo Waiting for the Blocks window (first launch / shader compile may take minutes) ...
powershell -NoProfile -Command "$d=(Get-Date).AddSeconds(420); $p=$null; while((Get-Date) -lt $d){ $procs = Get-Process Blocks -ErrorAction SilentlyContinue; $win = $procs | Where-Object { $_.MainWindowHandle -ne 0 }; if ($win -and (Test-NetConnection 127.0.0.1 -Port 41451 -InformationLevel Quiet -WarningAction SilentlyContinue)) { exit 0 }; Start-Sleep -Seconds 3 }; exit 1"
if errorlevel 1 (
    echo Timeout: window did not appear. See env\Windows\Blocks\Saved\Logs\Blocks.log
    pause
    exit /b 1
)
echo Simulator ready! Taking off --

rem 3) Keyboard flight
rem    W/S forward-back   A/D left-right   Space/Shift up-down
rem    Q/E yaw   Esc land and exit   (release all keys = hover)
"C:\Users\rui\miniconda3\envs\cosys-airsim\python.exe" -u "E:\drone-sim\platforms\cosys-airsim\scripts\keyboard_flight.py"
pause
