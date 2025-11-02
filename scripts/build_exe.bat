@echo off
rem Script for building RumiaConfigurator executable on Windows
cd /d "%~dp0\.."
echo Working dir: %CD%

rem Kill any running instances of the app
taskkill /F /IM "RumiaConfigurator.exe" >nul 2>&1

rem Clean only build and dist folders
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

rem Verify resource files exist
if not exist "src\assets\Rumia_logo.png" (
    echo ERROR: Logo file not found at src\assets\Rumia_logo.png
    exit /b 1
)
if not exist "src\assets\Rumia_logo.ico" (
    echo ERROR: Icon file not found at src\assets\Rumia_logo.ico
    exit /b 1
)

rem PyInstaller command with simplified resource handling
if exist ".venv\Scripts\pyinstaller.exe" (
    .venv\Scripts\pyinstaller.exe --clean ^
        --onefile ^
        --noconsole ^
        --add-data "src/assets;assets" ^
        --icon "src/assets/Rumia_logo.ico" ^
        --name "RumiaConfigurator" ^
        --hidden-import=customtkinter ^
        --hidden-import=PIL ^
        --hidden-import=numpy ^
        --hidden-import=scipy ^
        --hidden-import=matplotlib ^
        --hidden-import=python-can ^
        --hidden-import=tkinter ^
        "src/RumiaConfigurator.py"
)

if %ERRORLEVEL% EQU 0 (
    echo Build completed. Exe in dist\
) else (
    echo Error during the build process.
)
pause