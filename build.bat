REM pls make sure you've installed build & twine: pip install --upgrade build twine

REM Clean previous build artifacts
call clean.bat

REM Copy vendor dependencies into oddtts/vendor/ before building
python vendor_build.py

REM Build the package
python -m build

REM Clean up vendored source after build
python vendor_build.py clean
