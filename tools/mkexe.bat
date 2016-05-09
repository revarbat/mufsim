SET TCL_LIBRARY=C:\Python27\tcl\tcl8.5
SET TK_LIBRARY=C:\Python27\tcl\tk8.5
PATH=%PATH%;C:\Python\mufsimenv;C:\Python\mufsimenv\Scripts;C:\Python27\Scripts
pyinstaller --windowed --onefile --name mufsim mufgui\mufgui.py
powershell.exe -nologo -noprofile -command "& { Add-Type -A 'System.IO.Compression.FileSystem'; [IO.Compression.ZipFile]::CreateFromDirectory('foo', 'foo.zip'); }"

