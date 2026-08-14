REM pls make sure you've installed build & twine: pip install --upgrade build twine

REM Clean previous build artifacts
echo Cleaning previous build artifacts...
if exist dist rd /s /q dist
if exist build rd /s /q build
if exist oddtts.egg-info rd /s /q oddtts.egg-info

REM Build the package
python -m build
