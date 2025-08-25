@echo off
setlocal enabledelayedexpansion
title P4V Monitor: ProjectB
echo ========================================
echo P4V Project Manager - Monitor Mode
echo ========================================
echo Project: ProjectB
echo Scripts Path: O:\Person\Projects\interview\TestProject\P4VProjectManager\TestFiles\Project_2
echo Start Time: %date% %time%
echo ========================================
echo.
echo Monitoring for build commands...
echo.
:MAIN_LOOP
set /p COMMAND=<"O:\Person\Projects\interview\TestProject\P4VProjectManager\TestFiles\Project_2\_command_ProjectB.txt" 2>nul
if "!COMMAND!"=="BUILD" (
    echo.
    echo ========================================
    echo New build request received!
    echo Time: %date% %time%
    echo ========================================
    echo.
    echo RUNNING > "O:\Person\Projects\interview\TestProject\P4VProjectManager\TestFiles\Project_2\_status_ProjectB.txt"
    echo WAIT > "O:\Person\Projects\interview\TestProject\P4VProjectManager\TestFiles\Project_2\_command_ProjectB.txt"
    echo [1/3] Executing: prebuild.bat
    echo ----------------------------------------
    echo RUNNING:prebuild.bat > "O:\Person\Projects\interview\TestProject\P4VProjectManager\TestFiles\Project_2\_status_ProjectB.txt"
    call "O:\Person\Projects\interview\TestProject\P4VProjectManager\TestFiles\Project_2\prebuild.bat" "ProjectB"
    if errorlevel 1 (
        echo [ERROR] Script prebuild.bat failed with error code !errorlevel!
        echo ERROR:prebuild.bat:!errorlevel! >> "O:\Person\Projects\interview\TestProject\P4VProjectManager\TestFiles\Project_2\_status_ProjectB.txt"
    ) else (
        echo [SUCCESS] Script prebuild.bat completed
        echo COMPLETED:prebuild.bat >> "O:\Person\Projects\interview\TestProject\P4VProjectManager\TestFiles\Project_2\_status_ProjectB.txt"
    )
    echo.
    echo [2/3] Executing: build.bat
    echo ----------------------------------------
    echo RUNNING:build.bat > "O:\Person\Projects\interview\TestProject\P4VProjectManager\TestFiles\Project_2\_status_ProjectB.txt"
    call "O:\Person\Projects\interview\TestProject\P4VProjectManager\TestFiles\Project_2\build.bat" "ProjectB"
    if errorlevel 1 (
        echo [ERROR] Script build.bat failed with error code !errorlevel!
        echo ERROR:build.bat:!errorlevel! >> "O:\Person\Projects\interview\TestProject\P4VProjectManager\TestFiles\Project_2\_status_ProjectB.txt"
    ) else (
        echo [SUCCESS] Script build.bat completed
        echo COMPLETED:build.bat >> "O:\Person\Projects\interview\TestProject\P4VProjectManager\TestFiles\Project_2\_status_ProjectB.txt"
    )
    echo.
    echo [3/3] Executing: postbuild.bat
    echo ----------------------------------------
    echo RUNNING:postbuild.bat > "O:\Person\Projects\interview\TestProject\P4VProjectManager\TestFiles\Project_2\_status_ProjectB.txt"
    call "O:\Person\Projects\interview\TestProject\P4VProjectManager\TestFiles\Project_2\postbuild.bat" "ProjectB"
    if errorlevel 1 (
        echo [ERROR] Script postbuild.bat failed with error code !errorlevel!
        echo ERROR:postbuild.bat:!errorlevel! >> "O:\Person\Projects\interview\TestProject\P4VProjectManager\TestFiles\Project_2\_status_ProjectB.txt"
    ) else (
        echo [SUCCESS] Script postbuild.bat completed
        echo COMPLETED:postbuild.bat >> "O:\Person\Projects\interview\TestProject\P4VProjectManager\TestFiles\Project_2\_status_ProjectB.txt"
    )
    echo.
    echo ========================================
    echo Build completed!
    echo End Time: %date% %time%
    echo ========================================
    echo.
    echo IDLE > "O:\Person\Projects\interview\TestProject\P4VProjectManager\TestFiles\Project_2\_status_ProjectB.txt"
    echo Waiting for next build command...
    echo.
) else if "!COMMAND!"=="EXIT" (
    echo.
    echo Received exit command. Shutting down...
    exit
)
timeout /t 1 /nobreak >nul
goto MAIN_LOOP
