@echo off
REM Setup Ollama for Windows / RTX 3060

echo ============================================
echo Setting up Ollama for Windows / RTX 3060
echo ============================================
echo.

REM Check if Ollama is installed
where ollama >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing Ollama...
    echo Please download from: https://ollama.com/download/windows
    echo.
    pause
    exit /b 1
)

echo Starting Ollama service...
start /B ollama serve
timeout /t 5 /nobreak >nul

echo.
echo Pulling TinyLlama (1.1B) - 637MB...
ollama pull tinyllama

echo.
echo Pulling StableLM 2 (1.6B) - 1.1GB...
ollama pull stablelm2:1.6b

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Installed Models:
ollama list

echo.
echo Testing Recommendation Model (TinyLlama)...
ollama run tinyllama "Recommend 2 jackets for casual style. Be brief."

echo.
echo Testing Inventory Model (StableLM2)...
ollama run stablelm2:1.6b "Check stock: SKU_JCK_01. Format: JSON"

echo.
echo ========================================
echo Next Steps:
echo   1. Run: python recommendation-agent\agent_local_llm.py
echo   2. Run: python inventory-agent\agent_local_llm.py
echo.
echo Memory Usage (RTX 3060 6GB):
echo   - TinyLlama: ~600MB VRAM
echo   - StableLM2: ~1.1GB VRAM
echo   - Total: ~1.7GB (leaves 4.3GB free)
echo ========================================
pause
