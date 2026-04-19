set DIR=C:\Users\ipetrash\PycharmProjects\run-tasks
set PYTHON=%DIR%\.venv\Scripts\python.exe

cd %DIR%\src
%PYTHON% -m run_tasks.app_task_manager.main
