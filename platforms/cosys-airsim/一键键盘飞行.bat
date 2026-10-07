@echo off
title Cosys-AirSim Keyboard Flight (one-click)

rem 1) Start Blocks simulator (skip if already running)
powershell -NoProfile -Command "if(-not (Get-Process Blocks -ErrorAction SilentlyContinue)){ Start-Process 'E:\drone-sim\platforms\cosys-airsim\env\Windows\Blocks.exe' -WorkingDirectory 'E:\drone-sim\platforms\cosys-airsim\env\Windows' }"

rem 2) Wait for RPC port (first launch may take 1-3 minutes for shader compile)
echo Waiting for Blocks simulator to be ready (first launch 1-3 minutes) ...
powershell -NoProfile -Command "$d=(Get-Date).AddSeconds(240); while((Get-Date) -lt $d){ try{ $c=New-Object Net.Sockets.TcpClient('127.0.0.1',41451); $c.Close(); exit 0 }catch{ Start-Sleep -Seconds 3 } }; exit 1"
if errorlevel 1 (
    echo Timeout: simulator did not start. Check the window / antivirus.
    pause
    exit /b 1
)
echo Simulator ready! Taking off --

rem 3) Keyboard flight
rem    W/S forward-back   A/D left-right   Space/Shift up-down
rem    Q/E yaw   Esc land and exit   (release all keys = hover)
"C:\Users\rui\miniconda3\envs\cosys-airsim\python.exe" -u "E:\drone-sim\platforms\cosys-airsim\scripts\keyboard_flight.py"
pause
