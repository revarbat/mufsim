all:
	@echo "Nothing to do."

test:
	cd tests && ./runtests.sh

install:
	python3 setup.py build install -f

release:
	rm -rf dist/MufSim-*.egg dist/MufSim-*.tar.gz dist/MufSim-*.whl
	python3 setup.py egg_info sdist bdist_wheel bdist_egg

upload:
	twine upload dist/*.tar.gz dist/*.whl dist/*.egg

app:
	rm -rf dist/MufSim dist/MufSim.app dist/MufSimOSX.zip
	python3 setup.py py2app
	rm -rf dist/MufSim
	tools/mkicons.sh
	cp icons/MufSim.icns dist/MufSim.app/Contents/Resources/
	mkdir -p dist/MufSim.app/Contents/Resources/muv
	cp /usr/local/bin/muv dist/MufSim.app/Contents/Resources/muv/
	cp -a /usr/local/share/muv/incls dist/MufSim.app/Contents/Resources/muv/incls
	cd dist && zip -r MufSimOSX MufSim.app

exe:
	rm -rf dist/MufSim dist/MufSim.exe dist/MufSimWin64.zip
	pyinstaller MufSim.spec
	# cd dist && zip -r MufSimWin64 MufSim.exe

py2exe:
	rm -rf dist/MufSim dist/MufSim.exe dist/MufSimWin64.zip
	python3 setup.py py2exe
	# cd dist && zip -r MufSimWin64 MufSim.exe

clean:
	rm -rf build *.pyc __pycache__
	find mufsim -name '*.pyc' -o -name __pycache__ -o -name .ropeproject | xargs rm -rf

distclean: clean
	rm -rf dist dist-win

