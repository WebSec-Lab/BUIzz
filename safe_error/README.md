# safe_error/

Tracks corpus URLs that error out during baseline collection.

When `base_line.py` runs, any URL that fails is recorded in
`err-list-need-mouse.txt`. The file starts empty and is filled automatically at runtime.
