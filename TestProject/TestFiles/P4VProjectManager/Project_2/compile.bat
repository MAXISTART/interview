@echo off
echo ========================================
echo Starting compilation process (test version)...
echo Current time: %date% %time%
echo ========================================

:: Random error simulation (30% chance)
set /a "rand=%random% %% 100"

echo.
echo [Phase 1] Syntax checking...
echo Checking file: main.cpp [OK]
echo Checking file: utils.cpp [OK]
echo Checking file: core.cpp [OK]

:: If random number < 30, simulate compile error
if %rand% LSS 30 (
    echo.
    echo [ERROR] Compilation failed: Syntax error found!
    echo source.cpp(42): error C2065: 'undefined_var': undeclared identifier
    echo.
    echo Compilation aborted.
    exit /b 1
)

echo.
echo [Phase 2] Compiling source code...
for /L %%i in (33,33,99) do (
    echo Compile progress: %%i%%
)
echo Compile progress: 100%%

:: Short delay
timeout /t 1 /nobreak >nul

echo.
echo [Phase 3] Code optimization...
echo Optimization level: O2
echo Optimization completed

echo Compiled Successfully > output.exe

echo.
echo ========================================
echo Compilation completed successfully!
echo Output: output.exe
echo Finish time: %date% %time%
echo ========================================
exit /b 0