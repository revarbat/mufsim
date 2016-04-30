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
	rm -rf dist/MufSimulator dist/MufSimulator.app dist/MufSimOSX.zip
	pyinstaller --noconfirm MufSimulator.spec
	rm -rf dist/MufSimulator
	cd dist && zip -r MufSimOSX MufSimulator.app

upload:
	twine upload dist/*

clean:
	rm -rf build dist/MufSimulator*

