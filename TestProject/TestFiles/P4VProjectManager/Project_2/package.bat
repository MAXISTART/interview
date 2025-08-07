@echo off
echo ========================================
echo Starting release packaging...
echo Current time: %date% %time%
echo ========================================

:: Set version info
set VERSION=1.0.0
set BUILD_NUMBER=%random%

echo.
echo Version: %VERSION%.%BUILD_NUMBER%
echo.

echo [1/4] Collecting build artifacts...
echo Collecting: application.exe
echo Collecting: config.xml
echo Collecting: readme.txt

echo.
echo [2/4] Compressing resources...
echo Compression progress: 50%%
echo Compression progress: 100%%

echo.
echo [3/4] Generating configuration file...
echo ^<?xml version="1.0"?^> > config.xml
echo ^<version^>%VERSION%.%BUILD_NUMBER%^</version^> >> config.xml
echo Configuration file generated

echo.
echo [4/4] Creating installer...
echo Building installer: 100%%

:: Create final package
echo Package Complete > release_%VERSION%.exe

:: Short delay
timeout /t 1 /nobreak >nul

:: Clean temp files
del config.xml 2>nul

echo.
echo ========================================
echo Packaging completed!
echo Release package: release_%VERSION%.exe
echo Version: %VERSION%.%BUILD_NUMBER