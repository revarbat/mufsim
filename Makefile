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
	rm -rf dist/MufSim dist/MufSim.app dist/MufSimOSX.zip dist/MufSimOSX64.zip
	pyinstaller MufSim.spec
	rm -rf dist/MufSim
	tools/mkicons.sh
	cp icons/MufSim.icns dist/MufSim.app/Contents/Resources/
	cd dist && zip -r MufSimOSX64 MufSim.app

exe:
	rm -rf dist/MufSim dist/MufSim.exe dist/MufSimWin64.zip
	pyinstaller MufSim.spec
	# cd dist && zip -r MufSimWin64 MufSim.exe


muvdoc: docs/MUVREF.html

docs/MUVREF.html: docs/MUVREF.rst docs/muvref.css
	cd docs && rst2html.py --stylesheet-path=html4css1.css,muvref.css --embed-stylesheet MUVREF.rst MUVREF.html

clean:
	rm -rf build *.pyc __pycache__
	find mufsim -name '*.pyc' -o -name __pycache__ -o -name .ropeproject | xargs rm -rf

distclean: clean
	rm -rf dist dist-win

