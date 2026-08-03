@echo off
chcp 65001 >nul
echo ========================================
echo 火电深度调峰+抽水蓄能优化计算
echo ========================================
echo.
echo 正在启动MATLAB优化程序...
echo 这可能需要较长时间，请耐心等待...
echo.

cd /d "%~dp0"

"C:\Program Files\MATLAB\R2024b\bin\matlab.exe" -nodisplay -r "cd('c:/Users/mu''yan''shi''qi/Desktop/火电深度调峰+抽水蓄能/全年抽蓄减碳效益优化计算'); main; exit;"

echo.
echo 优化完成！
pause