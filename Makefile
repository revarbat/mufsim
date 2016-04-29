all:
	@echo "Nothing to do."

install:
	python setup.py build install

test:
	cd tests && ./runtests.sh

nightly:
	python setup.py egg_info --tag-date --tag-build=DEV bdist_egg

release:
	python setup.py egg_info bdist_egg

upload:
	twine upload dist/*

