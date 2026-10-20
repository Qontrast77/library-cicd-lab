@echo off
rem Virtual environment for the ML part (created once, then only package check)
if not exist venv-ml\Scripts\python.exe "%PYTHON%" -m venv venv-ml
venv-ml\Scripts\python.exe -m pip install --disable-pip-version-check -q -r ml\requirements.txt
if errorlevel 1 exit /b 1
venv-ml\Scripts\python.exe -c "import mlflow, sklearn; print('mlflow', mlflow.__version__, '| scikit-learn', sklearn.__version__)"
