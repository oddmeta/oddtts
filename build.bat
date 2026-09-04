REM pls make sure you've installed build & twine: pip install --upgrade build twine

REM Clean previous build artifacts
call clean.bat

REM Build the package
python setup.py bdist_wheel
