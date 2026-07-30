@echo off
title RESILIENT POCKET — AI Financial Risk & Cash Copilot Server
cls
echo ==================================================================
echo   LAUNCHING RESILIENT POCKET WEB DASHBOARD SERVER
echo ==================================================================
echo.
echo Opening server at http://localhost:8080 ...
echo Press Ctrl+C in this terminal window anytime to stop the server.
echo.
"C:\Users\Amrutha\anaconda3\python.exe" -u web_server.py
pause
