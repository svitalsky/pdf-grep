#!/bin/sh

cd "$( dirname "$0" )"

[ -d "$HOME/bin" ] && \
    [ -f pdf-grep.py ] && \
    /bin/cp -v -f pdf-grep.py "$HOME/bin/pdf-grep" && \
    chmod 755 -v "$HOME/bin/pdf-grep"
