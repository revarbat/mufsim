all:
	@echo "Nothing to do."

install:
	cp mufsim /usr/local/bin/mufsim

test:
	cd tests && ./runtests.sh

