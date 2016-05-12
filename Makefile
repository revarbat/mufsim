all:
	@echo "Nothing to do."

install:
	python3 setup.py build install -f

test:
	cd tests && ./runtests.sh

nightly:
	python3 setup.py egg_info --tag-date --tag-build=DEV bdist_egg

release:
	rm -rf dist/MufSim-*.egg
	python3 setup.py egg_info bdist_egg

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
	python3 setup.py py2exe
	cd dist && zip -r MufSimWin64 MufSim.exe

upload:
	twine upload dist/*.egg

clean:
	rm -rf build dist/MufSimulator* dist/MufSim.app dist/mufsim.exe dist/mufsim
	find . -name '*.pyc' -exec rm {} \;

