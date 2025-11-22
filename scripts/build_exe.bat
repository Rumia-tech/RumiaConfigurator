@echo off
rem Script for building RumiaConfigurator executable on Windows
cd /d "%~dp0\.."
echo Working dir: %CD%

rem Kill any running instances of the app
taskkill /F /IM "RumiaConfigurator.exe" >nul 2>&1

rem Clean only build and dist folders
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
del /f /q RumiaConfigurator.spec 2>nul

rem Verify resource files exist
if not exist "src\assets\Rumia_logo.png" (
    echo ERROR: Logo file not found at src\assets\Rumia_logo.png
    exit /b 1
)
if not exist "src\assets\Rumia_logo.ico" (
    echo ERROR: Icon file not found at src\assets\Rumia_logo.ico
    exit /b 1
)

REM Verifying required modules exist
for %%F in (gui.py can_interface.py plot_manager.py utils.py plotting.py RumiaConfigurator.py) do (
    if not exist "src\%%F" (
        echo [ERROR] Missing module: src\%%F
        exit /b 1
    )
)

REM Activate venv if present (otherwise use global Python)
if exist ".venv\Scripts\python.exe" (
    call ".venv\Scripts\activate.bat"
) else (
    echo [INFO] venv not found: creating and installing minimal dependencies.
    py -3 -m venv .venv || (echo [ERROR] Failed to create venv & exit /b 1)
    call ".venv\Scripts\activate.bat"
)

REM Update pip silently
python -m pip install --upgrade pip >nul 2>&1

REM Ensure pyinstaller is installed
python -m pip show pyinstaller >nul 2>&1 || python -m pip install pyinstaller || (echo [ERROR] PyInstaller installation failed & exit /b 1)
REM Install project dependencies (if requirements present)
if exist requirements.txt (
    echo [INFO] Installing requirements...
    python -m pip install -r requirements.txt || (echo [ERROR] Install requirements failed & exit /b 1)
)

REM Build debug (with console) to verify CAN interfaces
echo [INFO] Building debug exe (console visibile)...
pyinstaller ^
  src\RumiaConfigurator.py ^
  --name RumiaConfigurator_debug ^
  --onefile ^
  --icon src\assets\Rumia_logo.ico ^
  --add-data "src\assets;assets" ^
  --hidden-import gui ^
  --hidden-import can_interface ^
  --hidden-import plot_manager ^
  --hidden-import utils ^
  --hidden-import plotting ^
  --hidden-import customtkinter ^
  --hidden-import darkdetect ^
  --hidden-import serial ^
  --hidden-import serial.tools.list_ports ^
  --hidden-import can ^
  --hidden-import can.interfaces ^
  --hidden-import can.interfaces.slcan ^
  --hidden-import can.interfaces.virtual || (echo [ERROR] Debug build failed & exit /b 1)

REM Build release (noconsole)
echo [INFO] Building release exe (noconsole)...
pyinstaller ^
  src\RumiaConfigurator.py ^
  --name RumiaConfigurator ^
  --onefile ^
  --noconsole ^
  --icon src\assets\Rumia_logo.ico ^
  --add-data "src\assets;assets" ^
  --hidden-import gui ^
  --hidden-import can_interface ^
  --hidden-import plot_manager ^
  --hidden-import utils ^
  --hidden-import plotting ^
  --hidden-import customtkinter ^
  --hidden-import darkdetect ^
  --hidden-import serial ^
  --hidden-import serial.tools.list_ports ^
  --hidden-import can ^
  --hidden-import can.interfaces ^
  --hidden-import can.interfaces.slcan ^
  --hidden-import can.interfaces.virtual || (echo [ERROR] Release build failed & exit /b 1)

echo [SUCCESS] Build complete. Files:
dir /b dist\RumiaConfigurator*.exe

echo.
echo Avvia debug per test CAN: dist\RumiaConfigurator_debug.exe
echo Avvia release:          dist\RumiaConfigurator.exe

endlocal
pause