SET TCL_LIBRARY=C:\Python34\tcl\tcl8.5
SET TK_LIBRARY=C:\Python34\tcl\tk8.5
rem PATH=%PATH%;C:\Python\mufsimenv;C:\Python\mufsimenv\Scripts;C:\Python27\Scripts

del dist\MufSim.exe
pyinstaller MufSim.spec
rem pyinstaller --windowed --onefile --name MufSim kickstart.py

cd dist
del MufSimWin64.zip
rmdir /s /q MufSimWin64
mkdir MufSimWin64
copy MufSim.exe MufSimWin64
powershell.exe -nologo -noprofile -command "& { Add-Type -A 'System.IO.Compression.FileSystem'; [IO.Compression.ZipFile]::CreateFromDirectory('MufSimWin64', 'MufSimWin64.zip'); }"
rmdir /s /q MufSimWin64
cd ..


