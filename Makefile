all:
	@echo "Nothing to do."

install:
	python setup.py build install -f

test:
	cd tests && ./runtests.sh

nightly:
	python setup.py egg_info --tag-date --tag-build=DEV bdist_egg

release:
	python setup.py egg_info bdist_egg

apps:
	rm -rf dist/MufSimulator dist/MufSimulator.app dist/MufSim.app dist/MufSimOSX.zip
	python setup.py py2app
	rm -rf dist/MufSimulator
	cp osxbundlefiles/icon-windowed.icns dist/MufSim.app/Contents/Resources/
	cd dist && zip -r MufSimOSX MufSim.app

upload:
	twine upload dist/*

clean:
	rm -rf build dist/MufSimulator* dist/MufSim.app

