all:
	@echo "Nothing to do."

install:
	python setup.py build install -f

test:
	cd tests && ./runtests.sh

nightly:
	python setup.py egg_info --tag-date --tag-build=DEV bdist_egg

release:
	rm -rf dist/MufSim-*.egg
	python setup.py egg_info bdist_egg

apps:
	rm -rf dist/MufSimulator dist/MufSimulator.app dist/MufSim.app dist/MufSimOSX.zip
	python setup.py py2app
	rm -rf dist/MufSimulator
	tools/mkosxicns.sh
	cp osxbundlefiles/MufSim.icns dist/MufSim.app/Contents/Resources/
	mkdir -p dist/MufSim.app/Contents/Resources/muv
	cp /usr/local/bin/muv dist/MufSim.app/Contents/Resources/muv/
	cp -a /usr/local/share/muv/incls dist/MufSim.app/Contents/Resources/muv/incls
	cd dist && zip -r MufSimOSX MufSim.app

upload:
	twine upload dist/*.egg

clean:
	rm -rf build dist/MufSimulator* dist/MufSim.app

