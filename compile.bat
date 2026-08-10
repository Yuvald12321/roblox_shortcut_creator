call ".venv\Scripts\pyinstaller.exe" --onefile --noconsole --icon "logo.ico" -n "RSC" main.py
rd /S /Q "build"