init:
    pip install -r requirements.txt

help:
	python3 mwg/main.py --help

.PHONY: init help