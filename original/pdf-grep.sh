#!/bin/bash

printHelp() {
    cat <<EOF

    A script to search PDF(s) for occurrences of a searched pattern, count them and
    open the results in the 'less' text viewer. Expects 'grep', 'pdftottext' and 'less'
    to be present on your system.

    Usage:
        pdf-grep -h
        pdf-grep [-i] [file1.pdf] [file2.pdf] [...] [dir1] [dir2] [...] [not exclude-mask...] [-p] {pattern}

    Options and parameters:
        -h:         will print this help and exits.
        -i:         search is case sensitive by default, this option makes it case insensitive.
        -p:         optionally specify explicitly that the next argument is a search pattern,
                    e.g. when you need to search for the reserved word 'not' (see bellow).

        fileN.pdf:  file to be searched in, may be repeated.
        dirN:       directory to be searched in (NOT recursively!), may be repeated; in each
                    directory all the PDF files (i.e. having the .pdf suffix — suffix is case
                    insensitive, so the file 'dir/file.PDF' is counted in as well) are included.
        At least one PDF file or directory must be given.

        not exlude-mask...:
                    'not' is a reserved word after which must come exactly one argument 'exclude-mask...'
                    It may appear in this capacity at most once, any other occurrence will be treated
                    normally, i.e. as directory or search pattern. 'exclude-mask...' means beginning
                    of PDF file names to be excluded from search.
        pattern:    is a search pattern, must occur exactly once, may contain regexp, may be introduces
                    with '-p'.

    Examples:
        pdf-grep "my text" file.pdf
            This will search for 'my text' in the 'file.pdf' file.

        pdf-grep "my text" directory/file*
            This will search for 'my text' in whatever (files and/or directories) the shell returns
            as the result of expanding the '*' wildcard in the 'directory/file*' expression.

        pdf-grep file.pdf some/directory "reflex[eií]" -i some/other/directory
            This will search for regexp pattern "reflex[eií]" in the file 'file.pdf' (must exist,
            otherwise its name would be treated as search pattern and the real pattern would be
            considered the second one which would of course cause error exit) and in any PDF found in
            the 'some/directory' or 'some/other/directory' directories (again, both the directories
            must exist for the same reason as above). The search will be case insensitive.

        pdf-grep not/ not not -p not
            This will search for pattern 'not' in PDFs in the directory 'not' (notice the slash at
            the end of the directory name to distinguish it from both pattern and the 'not' reserved
            word), excluding any PDF file the name of which begins with 'not'.

        pdf-grep not not not some/dir
            This will search for pattern 'not' in PDFs in the 'some/dir' directory, excluding any PDF
            file the name of which begins with 'not'. Here we didn't need to specify the search pattern
            with explicit '-p' option because it couldn't get confused with the 'not' directory.

    WARNING: in case some PDF file is included twice (or more) in the search (e.g. is specified explicitly
             twice on command line, or is both named as a file and located in a named directory), you will
             get twice (or more) as many hits for your search pattern. This script doesn't do any check
             whatsoever for any duplicity in searched files and/or directories. It is therefore up to you
             to ensure each file is included exactly once or to deal with the consequences otherwise.

EOF
}


errorExit() {
    [ "$1" != "" ] && ERRMSG="$1" || ERRMSG="Unknown error occurred."
    echo "$ERRMSG Exiting now!" >&2
    exit 1
}


dirHasPdfs() {
    if [[ -d $1 ]] ; then
        answ="no"
        for pdf in ${1}/*.[Pp][Dd][Ff] ; do
            [[ -f $pdf ]] && answ="yes"
        done
        echo $answ
    else
        echo "no"
    fi
}


ARG_SET=0
NOT_SET=0
EXPECT_NOT=0
EXPECT_PAT=0
PARAMS=""
NOT_IN=""
IC_GREP=""


setSearchPattern() {
    if [ "$1" != "" ] ; then
        ARG_SET=1
        GREP_FOR="$1"
        EXPECT_PAT=0
    else
        errorExit "Cannot search for an empty pattern."
    fi
}


setNotMask() {
    NOT_IN="$1"
    NOT_SET=1
    EXPECT_NOT=0
}


for arg in "$@" ; do
    if [ "$arg" = "-h" ] ; then
        printHelp
        exit 0
    elif [ "$arg" = "-p" ] ;then
        EXPECT_PAT=1
    elif [ $EXPECT_NOT -eq 1 ] ; then
        setNotMask "$arg"
    elif [ $EXPECT_PAT -eq 1 ] ; then
        setSearchPattern "$arg"
    else
        if [ "$arg" = "not" ] ; then
            [ $NOT_SET -eq 0 ] && { EXPECT_NOT=1 ; continue ; }
        fi
        if [[ -f $arg ]] ; then
            PARAMS="$PARAMS $arg"
        elif [[ -d $arg ]] ; then
            [ "$( dirHasPdfs "$arg" )" = "yes" ] && \
                PARAMS="$PARAMS $arg/*.[Pp][Dd][Ff]"
        elif [ "$arg" = "-i" ] ; then
            IC_GREP="-i"
        elif [ $ARG_SET -eq 0 ] ; then
            ARG_SET=1
            GREP_FOR="$arg"
        else
            errorExit "Unrecognized parameter '$arg'."
        fi
    fi
done

[ $ARG_SET -eq 0 ] && errorExit "Grep for what?"
[ "$PARAMS" = "" ] && errorExit "Grep where?"


append() {
    output="${output}$( echo -e "\n${1}" )"
}

total=0
output=""
for pdf in $PARAMS ; do
    if [ $NOT_SET -eq 1 ] ; then
        LEN=${#NOT_IN}
        PDF_BASE="$( basename "$pdf" )"
        [ "${PDF_BASE:0:$LEN}" = "$NOT_IN" ] && continue
    fi
    hits=$(pdftotext $pdf - | grep $IC_GREP -c "$GREP_FOR")
    total=$(( total + hits ))
    if [ $hits -gt 0 ]; then
        [ $hits -gt 1 ] && \
            hit_word=hits || \
            hit_word=hit
        pdf_name="$(basename $pdf | sed s/\_.*//) ($( dirname $pdf )/)"
        append "\n*********************************************************************************************"
        append "*** $pdf_name: $hits $hit_word"
        append "$( pdftotext $pdf - | grep $IC_GREP "$GREP_FOR" | sed 's/^/\n/' )"
    fi 
done

[ "$IC_GREP" != "" ] && IC_GREP="-I"

{
echo "*** Total hits: $total"
echo "$output"
} | less $IC_GREP -p"$GREP_FOR|^\*\*\* Total hits:"

exit $?

