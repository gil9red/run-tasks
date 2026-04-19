set DIR=C:\Users\ipetrash\PycharmProjects\run-tasks
set PYTHON=%DIR%\.venv\Scripts\python.exe
set FLASK_DEBUG=false

cd %DIR%\src
%PYTHON% -m run_tasks.app_web.main
