# Запуск сайта на своём компьютере одной командой:
#   powershell -ExecutionPolicy Bypass -File run.ps1
# Что делает: создаёт .venv (если нет), ставит пакеты, готовит базу и контент, запускает сайт на http://localhost:3000
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "1. Создаю виртуальное окружение .venv ..."
    py -3.13 -m venv .venv
}
Write-Host "2. Ставлю пакеты из requirements.txt ..."
& .venv\Scripts\python.exe -m pip install --disable-pip-version-check -q -r requirements.txt
Write-Host "3. Готовлю базу, админа и контент ..."
& .venv\Scripts\python.exe manage.py setup
Write-Host "4. Сайт: http://localhost:3000   Админка: http://localhost:3000/admin/   (остановить — Ctrl+C)"
& .venv\Scripts\python.exe manage.py runserver 3000
