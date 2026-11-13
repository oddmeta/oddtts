REM pls make sure you've installed build & twine: pip install --upgrade build twine

REM Clean previous build artifacts
call clean.bat

REM Copy vendor dependencies into oddtts/vendor/ before building
python vendor_build.py

REM Build the package (PYTHONUTF8=1 fixes GBK encoding error on Chinese Windows)
set PYTHONUTF8=1
python -m build

REM Clean up vendored source after build
python vendor_build.py clean
