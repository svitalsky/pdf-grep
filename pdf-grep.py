#!/usr/bin/python
# coding=utf-8

from __future__ import print_function

import os
import re
import subprocess
import sys
import locale
import time

HELP = """
    A Python script to search PDF(s) for occurrences of a searched pattern, count them and
    open the results in the 'less' text viewer or save them to a file. Expects 'pdftotext'
    (and optionally other tools such as 'less' or 'cat') to be present on your system.

    Usage:
        pdf-grep -h
        pdf-grep [-q] [-i] [-c] [fileN.pdf ...] [dirN ...] [not exclude-mask] [-s {file|-}] <[-p] pattern>

    Options and parameters:
        The order of parameters is mostly irrelevant, apart from obvious pairs '[-p] pattern', '-s file'
        and 'not exclude-mask'.
        -h:          print this help and exit.
        -q:          be quiet in case nothing is found ('No hits (in xx ms)' is reported by default)
        -i:          make the search case insensitive; it is case sensitive by default.
        -c:          show clean lines, i.e. do not prepend lines with their respective approximate
                     position in a file; by default each line with a hit is included in results prepended
                     with approximate position, e.g. "(23%) the actual text of the line"
        -p:          optionally specify explicitly that the next argument is a search pattern,
                     e.g. when you need to search for the reserved word 'not' (see bellow).
        -s {file|-}: don't open the results in 'less', rather save them to the file; fails if the file
                     is a regular file and already exists; use '-' to just print the results to
                     the standard output

        fileN.pdf:   file to be searched in, may be repeated.
        dirN:        directory to be searched in (NOT recursively!), may be repeated; in each
                     directory all the PDF files (i.e. having the .pdf suffix — suffix is case
                     insensitive, so the file 'dir/file.PDF' is counted in as well) are included.
        
        At least one PDF file or a directory containing one must be given!

        not exclude-mask:
                     'not' is a reserved word after which must come exactly one argument 'exclude-mask'
                     It may appear in this capacity once at most, any other occurrence will be treated
                     normally, i.e. as file, directory or search pattern. The 'exclude-mask' means
                     beginning of PDF file names to be excluded from search.
        pattern:     is a search pattern, must occur exactly once, may contain regexp, may be introduced
                     with '-p'.

    Examples:
        pdf-grep "my text" file.pdf
            This will search for 'my text' in the 'file.pdf' file.

        pdf-grep "my text" directory/file* -s -
            This will search for 'my text' in whatever (files and/or directories) the shell returns
            as the result of expanding the '*' wildcard in the 'directory/file*' expression. The results
            will be printed to the standard output.

        pdf-grep file.pdf some/directory "reflex[eií]" -i some/other/directory
            This will search for regexp pattern "reflex[eií]" in the file 'file.pdf' (must exist,
            otherwise string 'file.pdf' would be treated as search pattern and the real pattern would be
            considered the second one which would of course cause error exit) and in any PDF found in
            the 'some/directory' or 'some/other/directory' directories (again, both the directories
            must exist for the same reason as above). The search will be case insensitive.

        pdf-grep not/ not not -p not
            This will search for pattern 'not' in PDFs in the directory 'not' (notice the slash at
            the end of the directory name to distinguish it from both pattern and the 'not' reserved
            word), excluding any PDF file the name of which begins with 'not'.

        pdf-grep not mask not some/dir
            This will search for pattern 'not' in PDFs in the 'some/dir' directory, excluding any PDF
            file the name of which begins with 'mask'. Here we didn't need to introduce the 'not' search
            pattern with explicit '-p' because it couldn't get confused with the directory name as in
            the previous example.
"""


def errorExit(cause):
    print(cause + " Exiting now!", file=sys.stderr)
    sys.exit(1)


def printHelp():
    print(HELP)
    sys.exit(0)


FILES_TO_SEARCH = []
PATTERN = ""
RE_PATTERN = None
NOT_IN = None
IC_GREP = ""
FILE_TO_SAVE = None
QUIET = False
CLEAN_LINES = False
expectNot = False
expectPat = False
expectFile = False


def setSearchPattern(par):
    global PATTERN, expectPat
    if par:
        PATTERN = par
        expectPat = False
    else:
        errorExit("Cannot search for an empty pattern.")


def setNotMask(par):
    global NOT_IN, expectNot
    NOT_IN = par
    expectNot = False


def setFile(par):
    global FILE_TO_SAVE, expectFile
    if par.strip():
        FILE_TO_SAVE = par.strip()
        expectFile = False
    else:
        errorExit("File name cannot be empty.")


def dirPDFs(directory):
    result = []
    for f in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, f)) \
                and len(f) > 3 \
                and f[-4:].lower() == '.pdf':
            result.append(os.path.join(directory, f))
    return result


def processParams(params):
    global IC_GREP, QUIET, CLEAN_LINES, expectNot, expectPat, expectFile
    for par in params:
        if expectPat: setSearchPattern(par)
        elif expectNot: setNotMask(par)
        elif expectFile: setFile(par)
        elif par == '-h': printHelp()
        elif par == '-p': expectPat = True
        elif par == '-s': expectFile = True
        elif par == '-i': IC_GREP = '-i'
        elif par == '-q': QUIET = True
        elif par == '-c': CLEAN_LINES = True
        elif par == 'not' and not NOT_IN: expectNot = True
        elif os.path.isfile(par): FILES_TO_SEARCH.append(par)
        elif os.path.isdir(par): FILES_TO_SEARCH.extend(dirPDFs(par))
        elif not PATTERN: setSearchPattern(par)
        else: errorExit("Unrecognized parameter '" + par + "'.")


def filterList(fileList):
    chklen = len(str(NOT_IN))
    temp = []
    for f in fileList:
        basename = os.path.basename(f)
        if len(basename) < chklen or basename[:chklen] != NOT_IN: temp.append(f)
    return temp


def sortList(data):
    localeBefore = locale.getlocale(locale.LC_ALL)
    locale.setlocale(locale.LC_ALL, 'cs_CZ.UTF-8')
    data = sorted(data, key=locale.strxfrm)
    locale.setlocale(locale.LC_ALL, localeBefore)
    return data


def normalizeFileList():
    global FILES_TO_SEARCH
    FILES_TO_SEARCH = list(set(FILES_TO_SEARCH))
    if NOT_IN: FILES_TO_SEARCH = sortList(filterList(FILES_TO_SEARCH))
    else: FILES_TO_SEARCH = sortList(FILES_TO_SEARCH)


def utf(asciiStr):
    return asciiStr.decode('utf-8')


def checkParams():
    global RE_PATTERN
    if not PATTERN: errorExit("Search for what?")
    elif str(PATTERN).find("\n") != -1: errorExit("Multiline search patterns are not supported.")
    elif IC_GREP: RE_PATTERN = re.compile(utf(PATTERN), re.UNICODE | re.IGNORECASE)
    else: RE_PATTERN = re.compile(utf(PATTERN), re.UNICODE)
    if not FILES_TO_SEARCH: errorExit("Search where?")
    if FILE_TO_SAVE and FILE_TO_SAVE != '-':
        if os.path.exists(FILE_TO_SAVE): errorExit("Output file '%s' already exists." % FILE_TO_SAVE)


def which(exeFile):
    def isExe(exeFile):
        return os.path.isfile(exeFile) and os.access(exeFile, os.X_OK)

    filePath, fileName = os.path.split(exeFile)
    if filePath:
        if isExe(exeFile): return exeFile
    else:
        for path in os.environ['PATH'].split(os.pathsep):
            exeFileFull = os.path.join(path, exeFile)
            if isExe(exeFileFull): return exeFileFull
    return None


def checkPrerequisites():
    prerequisites = ['pdftotext', ]
    if not FILE_TO_SAVE: prerequisites.extend(['less', 'cat', ])
    for item in prerequisites:
        if not which(item):
            errorExit("For this script to work '%s' must be installed and available." % item)


def positionLabel(lines, index):
    pos = 100.0 * index / len(lines)
    return '(%2d%s) ' % (pos, '%')


def searchInText(lines):
    result = {'lines': [], 'hits': 0}
    for index in range(len(lines)):
        line = utf(lines[index])
        found = RE_PATTERN.findall(line)
        if found:
            result['hits'] += len(found)
            if CLEAN_LINES: result['lines'].append(line)
            else: result['lines'].append(positionLabel(lines, index) + line)
    return result


def doSearch():
    total, lines, found = (0, 0, [])
    for f in FILES_TO_SEARCH:
        result = searchInText(subprocess.check_output(['pdftotext', f, '-']).splitlines())
        total += result['hits']
        if result['hits']:
            lines += len(result['lines'])
            found.append({'lines': result['lines'],
                          'hits': result['hits'],
                          'name': os.path.basename(f),
                          'dir': os.path.dirname(f)})
    return {'total': total, 'lines': lines, 'found': found}


def formatDuration(timeDuration):
    if timeDuration >= 10.0: return '%.1f s' % round(timeDuration, 1)
    elif timeDuration >= 1.0: return '%.2f s' % round(timeDuration, 2)
    else: return '%d ms' % (1000 * round(timeDuration, 3))


def openFile4Write(path):
    if os.path.isfile(path): return False
    try: return open(path, 'w')
    except: return False


def writeHeader(resultFile, result):
    resultFile.write('*** Searching for pattern "%s"\n' % PATTERN)
    if result['lines'] == 1: lineWord = 'line'
    else: lineWord = 'lines'
    if result['total'] == result['lines']:
        resultFile.write("*** Total hits: %d (in %s)\n" % (result['total'], duration))
    else:
        resultFile.write("*** Total hits: %d in %d %s (in %s)\n" %
                         (result['total'], result['lines'], lineWord, duration))


DELIMITER = "\n*********************************************************************************************\n"


def writeFileHeader(resultFile, found):
    resultFile.write(DELIMITER)
    if found['hits'] == 1: hitWord = 'hit'
    else: hitWord = 'hits'
    if len(found['lines']) == 1: lineWord = 'line'
    else: lineWord = 'lines'
    if found['dir']: dirLbl = ' [%s/]' % found['dir']
    else: dirLbl = ''
    if found['hits'] == len(found['lines']):
        resultFile.write("*** %s%s: %d %s\n\n" % (found['name'], dirLbl, found['hits'], hitWord))
    else:
        resultFile.write("*** %s%s: %d %s in %d %s\n\n" %
                         (found['name'], dirLbl, found['hits'], hitWord, len(found['lines']), lineWord))


def writeResults(resultFile):
    writeHeader(resultFile, results)
    for found in results['found']:
        writeFileHeader(resultFile, found)
        resultFile.writelines(map(lambda line: line.encode('utf-8') + '\n', found['lines']))


def saveResult():
    if FILE_TO_SAVE == '-': writeResults(sys.stdout)
    else:
        # check again here
        if os.path.exists(FILE_TO_SAVE): errorExit("Output file '%s' already exists." % FILE_TO_SAVE)
        resultFile = openFile4Write(FILE_TO_SAVE)
        if not resultFile: errorExit("Couldn't create result file '%s'." % FILE_TO_SAVE)
        writeResults(resultFile)
        resultFile.close()


def prepareOutput():
    tempFileBase = '.pdf-grep.' + str(os.getpid())
    tempDirs = ['/dev/shm', '/tmp', '/var/tmp', ]
    for tempDir in tempDirs:
        if not os.path.isdir(tempDir): continue
        tempFile = os.path.join(tempDir, tempFileBase)
        resultFile = openFile4Write(tempFile)
        if resultFile: return resultFile, tempFile
    errorExit("Couldn't create temporary file.")


def storeResult():
    resultFile, tempFile = prepareOutput()
    writeResults(resultFile)
    resultFile.close()
    return tempFile


def showOutput(tempFile):
    if IC_GREP: icLess = '-I'
    else: icLess = ''
    # do not open directly, go for pipe to facilitate 'Save to file' functionality of the less viewer
    os.system("cat " + tempFile + ' | less ' + icLess + '-p "' + PATTERN + '|^\*\*\* Total hits:" ')
    os.remove(tempFile)


def processResult():
    if FILE_TO_SAVE: saveResult()
    else: showOutput(storeResult())


if __name__ == "__main__":
    startTime = time.time()
    processParams(sys.argv[1:])
    normalizeFileList()
    checkParams()
    checkPrerequisites()
    results = doSearch()
    duration = formatDuration(time.time() - startTime)
    if results['total']: processResult()
    elif not QUIET: print("No hits (in %s)" % duration)
