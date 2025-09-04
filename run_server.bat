@echo off
REM Launch IOC Checker using Hypercorn in production
cd /d %~dp0
set PYTHONPATH=%~dp0%
python -m hypercorn ioc_checker.main:app --bind 0.0.0.0:8000
