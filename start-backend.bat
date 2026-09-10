@echo off
chcp 65001 >nul
echo ========================================
echo   FHZSK 后端服务启动脚本
echo   监听地址: 0.0.0.0:6005
echo ========================================
echo.

cd /d "%~dp0backend"

echo [1/3] 检查数据库连接...
python -c "import psycopg2; psycopg2.connect(host='127.0.0.1', port=5432, dbname='fhzsk', user='FHZSK', password='FHZSK123'); print('数据库连接正常')" 2>nul
if errorlevel 1 (
    echo [警告] 数据库连接失败！
    echo 请确保 PostgreSQL 已启动，或运行: docker-compose up -d
    echo.
    pause
    exit /b 1
)

echo.
echo [2/3] 执行数据库迁移...
python manage.py migrate --noinput
if errorlevel 1 (
    echo [错误] 数据库迁移失败
    pause
    exit /b 1
)

echo.
echo [3/3] 启动后端服务 (0.0.0.0:6005)...
echo.
echo 服务启动后，访问: http://127.0.0.1:6005/api/docs/
echo 按 Ctrl+C 停止服务
echo.

python manage.py runserver 0.0.0.0:6005
