set PYTHONPATH=C:\Users\ipetrash\PycharmProjects\run-tasks
cd %PYTHONPATH%

set PYTHON=venv\Scripts\python.exe
set FLASK_DEBUG=false
%PYTHON% %PYTHONPATH%\app_web\main.py
