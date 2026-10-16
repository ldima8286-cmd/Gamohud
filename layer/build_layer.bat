@echo off
REM Build the gamohud Vulkan layer on Windows (MinGW gcc or MSVC cl).
REM Requires the Vulkan SDK (VULKAN_SDK env var) with vulkan/vk_layer.h.
setlocal
cd /d "%~dp0"
if not exist "build" mkdir build

if "%VULKAN_SDK%"=="" (
    echo error: VULKAN_SDK is not set. Install the Vulkan SDK first.
    exit /b 1
)

where gcc >nul 2>nul
if %errorlevel%==0 (
    echo Building with MinGW gcc...
    gcc -O2 -Wall -Wextra -std=c99 -I"%VULKAN_SDK%\Include" -shared ^
        -o build\gamohud_layer.dll src\gamohud_layer.c -luser32
) else (
    where cl >nul 2>nul
    if %errorlevel%==0 (
        echo Building with MSVC cl...
        cl /nologo /O2 /LD /I"%VULKAN_SDK%\Include" /Fe:build\gamohud_layer.dll src\gamohud_layer.c
        del *.obj >nul 2>nul
    ) else (
        echo error: no C compiler found (need gcc or cl).
        exit /b 1
    )
)

REM Emit a Windows manifest pointing at the DLL.
> build\gamohud_layer.json (
    echo {
    echo     "file_format_version": "1.1.2",
    echo     "layer": {
    echo         "name": "VK_LAYER_GAMOHUD_overlay",
    echo         "type": "GLOBAL",
    echo         "library_path": "./gamohud_layer.dll",
    echo         "api_version": "1.1.0",
    echo         "implementation_version": "1",
    echo         "description": "gamohud frame counter layer",
    echo         "functions": {
    echo             "vkGetInstanceProcAddr": "vkGetInstanceProcAddr_gh",
    echo             "vkGetDeviceProcAddr": "vkGetDeviceProcAddr_gh"
    echo         },
    echo         "enable_environment": { "GAMOHUD_ENABLE": "1" },
    echo         "disable_environment": { "GAMOHUD_DISABLE": "1" }
    echo     }
    echo }
)

echo Built: build\gamohud_layer.dll
endlocal
