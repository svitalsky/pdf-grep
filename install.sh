#!/bin/sh

errorExit() {
    [ "$1" != "" ] && \
        errMsg="$1" || \
        errMsg="Unknown error"
    echo "$errMsg. Exiting now!" >&2
    exit 1
}

cd "$( dirname "$0" )"

[ $( id -u ) = 0 ] && \
    INST_DIR=/usr/local/bin || \
    INST_DIR=$HOME/bin

if ! [ -d "$INST_DIR" ] ; then
    mkdir "$INST_DIR" || errorExit "Failed to create installation directory '$INST_DIR'"
    echo "$PATH" | grep -q "$INST_DIR" || \
        echo "Please add the installation directory '$INST_DIR' to path!"
fi

if [ -f pdf-grep.py ] ; then
    /bin/cp -v -f pdf-grep.py "$INST_DIR/pdf-grep" && \
    chmod 755 -v "$INST_DIR/pdf-grep"
else
    errorExit "Cannot find the script 'pdf=grep.py' to install it. Please check or update your repository"
fi

exit 0
