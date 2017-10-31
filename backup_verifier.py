"""backup_verifier.py

MIT license
Copyright (c) 2016 by Doug Mahugh

Tool for analyzing a set of directory listings from backup drives and
identifying discrepancies: the extra, missing, or modified files on each drive.

add_quotes() -------> add quotes to a string if contains commas
backup_compare() ---> compare a backup to master, return differences
convert_to_csv() ---> Parse a text file containing a Windows directory listing
diff_report() ------> Generate difference analysis for a list of CSV files
display() ----------> Display a message and/or write it to report file
excluded_folder() --> Identify folders to be excluded (.git, etc.)
parseline() --------> Parse a line of text from a Windows directory listing
summary_msg() ------> Create a 1-liner summary message for a backup comparison
ts_to_datetime() ---> Convert Windows DIR timestamp to datetime value
"""
import csv
import datetime
import os
import sys
import time

#-------------------------------------------------------------------------------
def add_quotes(fieldvalue):
    """Add quotes to a string if it contains a comma.
    """
    return '"' + fieldvalue + '"' if ',' in fieldvalue else fieldvalue

#-------------------------------------------------------------------------------
def backup_compare(backup, master, report_file):
    """Compare a backup to a master copy, return the differences.

    backup = data file of the backup copy; either a .csv with four columns
             (folder/filename/timestamp/size) or a .dir capture of a Windows
             directory listing
    master = dictionary of the master, keys = filename, values = timestamp+size
    report_file = file handle to open report file for detailed output

    Returns (nmissing, ndiffer, nextra)
    """
    nmissing = 0
    ndiffer = 0
    nextra = 0
    display('analyzing ' + os.path.splitext(backup)[0] + ' ...', report_file, 'cn')
    display('>>> ' + os.path.splitext(backup)[0].upper() + ' <<<', report_file, 'f')
    backup_dict = {} # dictionary of this backup, populated in loop below

    if os.path.splitext(backup)[1].lower() == '.csv':
        datafile = backup
    else:
        datafile = os.path.splitext(backup)[0] + '.csv'
        display('parsing ' + backup + ' ...', report_file, 'cn')
        convert_to_csv(infile=backup, outfile=datafile)

    # scan through this backup and compare each file to master dictionary ...
    for row in csv.reader(open(datafile), delimiter=',', quotechar='"'):
        fullpath = row[0].lower() + '\\' + row[1].lower()
        ts_size = row[2] + row[3]
        backup_dict[fullpath] = ts_size
        if fullpath in master:
            if master[fullpath] != ts_size:
                display('modified: ' + fullpath, report_file, 'f')
                ndiffer += 1
        else:
            display('extra: ' + fullpath, report_file, 'f')
            nextra += 1

    # scan through master_dict to identify any files missing from the backup ...
    for fullpath in master:
        if fullpath not in backup_dict:
            display('missing: ' + fullpath, report_file, 'f')
            nmissing += 1

    return (nmissing, ndiffer, nextra)

#-------------------------------------------------------------------------------
def convert_to_csv(infile=None, outfile=None):
    """Parse a text file containing a Windows directory listing and write the
    data to a CSV file.

    infile = a file captured with a command such as DIR *.* /S >filename.dir
    outfile = name of a CSV file to be written
    """
    if not infile or not outfile:
        return # nothing to do

    # path = a string indicating the root path of the backup structure, so that
    # this can be removed from all data in the output file. This root path is
    # extracted from the first directory found in the input file below.
    path = None

    # open file, write header row to output file
    fhandle = open(outfile, 'w')
    fhandle.write('folder,filename,timestamp,bytes\n')

    lines_written = 0
    current_folder = None
    for line in open(infile, 'r'):
        linetext = line.strip()

        folder, filename, timestamp, filesize = parseline(linetext)
        if folder:
            # reset the current folder value, to  process files in this folder
            if not path:
                # path not set yet, so set it now. Note that the approach used
                # here is specific to our setup: a master server with a complete
                # backup stored under c:\backup-master, and a set of USB drives
                # with backups stored in the root of each one.
                if folder.startswith(r'c:\backup-master'):
                    path = r'c:\backup-master'
                else:
                    path = folder[0:2] # first 2 characters; e.g., 'd:'
            if folder.startswith(path):
                # remove the backup set root path from beginning of folder name
                current_folder = folder[len(path):]
            else:
                current_folder = folder
            continue

        if not filename:
            continue # not a filename, so nothing to do

        if excluded_folder(current_folder):
            continue

        # remove \backup-master from start of path ...
        if current_folder.startswith(r'\backup-master'):
            current_folder = current_folder[14:]

        datarow = add_quotes(current_folder) + ',' + add_quotes(filename) + \
            ',' + str(timestamp) + ',' + str(filesize)

        fhandle.write(datarow + '\n')
        lines_written += 1
        if lines_written % 10000 == 0:
            display('{0} lines parsed from {1} and written to '. \
                format(lines_written, infile) + outfile, None, 'cn')

    fhandle.close() #/// AFTER THIS, PRINT is BROKEN - ERRNO 9
    display('{} lines written to '.format(lines_written) + outfile, None, 'cn')

#-------------------------------------------------------------------------------
def diff_report(datafiles=None):
    """Generate a difference analysis for a list of data files.

    First entry in the list is the "master" copy for analysis purposes.

    Each file can be either a .csv file or a .dir file containing a Windows
    directory listing, in which case the same-named .csv file is created on the
    fly.

    A full-detail log file is created, and a brief summary on the console.
    """
    if not datafiles:
        # if no CSV files were specified, use our current defaults
        datafiles = ['master.csv', 'drive1.csv', 'drive2.csv', 'drive3.csv']

    # open output report file
    report_filename = 'backups-' + time.strftime("%Y-%m-%d-%H%M%S") + '.rpt'
    report_file = open(report_filename, 'w')
    display('log file: ' + report_filename, report_file)
    display('  MASTER: ' + datafiles[0], report_file, 'f')
    display('  copies: ' + str(datafiles[1:]), report_file, 'f')
    display('-'*80, report_file, 'f')

    # master_dict = a dictionary created from the master backup (first file)
    #    key = folder + r'\' + filename
    #    value = timestamp + filesize
    if os.path.splitext(datafiles[0])[1].lower() == '.csv':
        master_data = datafiles[0]
    else:
        display('parsing ' + datafiles[0] + ' ...', None, 'cn')
        master_data = os.path.splitext(datafiles[0])[0] + '.csv'
        convert_to_csv(datafiles[0], master_data)
    display('creating dictionary from MASTER COPY ...', report_file, 'cn')
    master_dict = {}
    for row in csv.reader(open(master_data, newline=''),\
        delimiter=',', quotechar='"'):
        master_dict[row[0].lower() + '\\' + row[1].lower()] = row[2] + str(row[3])

    masterfilesumm = os.path.splitext(datafiles[0])[0] + \
        ' -- MASTER COPY ({:,} files)'.format(len(master_dict))
    display(masterfilesumm, report_file)
    display('-'*80, report_file, 'f')

    # compare each backup against the master
    for nbackup, filename in enumerate(datafiles):
        if nbackup == 0:
            continue # skip the master
        nmissing, ndiffer, nextra = \
            backup_compare(filename, master_dict, report_file)
        summary = summary_msg(filename, datafiles[0], nmissing, ndiffer, nextra)
        display(summary, report_file)
        display('-'*80, report_file, 'f')

    report_file.close()

#-------------------------------------------------------------------------------
def display(message, report_file, flags='cf'):
    """Display a message and/or write it to report file

    message = the text message
    report_file = file handle of open report file
    flags = contains 'c' for console output and/or 'f' for file output;
            default is 'cf'; may also contain 'n' to suppress newline on
            console output
    """
    flags = flags.lower() if flags else 'cf'
    if len(message) < 80:
        message = message.ljust(80)
    if 'c' in flags:
        if 'n' in flags:
            print('\r' + message, end='')
        else:
            print('\r' + message)
    if 'f' in flags:
        report_file.write(message + '\n')

#-------------------------------------------------------------------------------
def excluded_folder(folder=None):
    """Determine whether a folder is to be excluded from the output CSV file.

    folder = a folder name
    Returns True if its contents should be excluded, false if not.
    """
    if not folder:
        return True

    if folder.endswith('__pycache__'):
        return True
    if folder.endswith('\\.git'):
        return True
    if '\\.git\\' in folder:
        return True
    if '\\$RECYCLE.BIN\\' in folder:
        return True

    return False

#-------------------------------------------------------------------------------
def parseline(linetext=None):
    """Parse a line from a directory listing, and return a tuple containing the
    folder name (if it's a Directory line), filename, timestamp, and filesize.
    """
    novalues = (None, None, None, None)
    if not linetext:
        return novalues

    # some lines are just noise, so don't parse them
    if ' <DIR> ' in linetext or 'File(s)' in linetext or \
        linetext.endswith('bytes free') or linetext.startswith('Volume ') \
        or linetext.startswith('Total Files'):
        return novalues

    if linetext.startswith('Directory of '):
        return (linetext[13:], None, None, None)
    else:
        filename = linetext[39:]
        timestamp = ts_to_datetime(linetext)
        filesize = int(linetext[20:38].strip().replace(',', ''))
        return (None, filename, timestamp, filesize)

#-------------------------------------------------------------------------------
def summary_msg(backup, master, nmissing, ndiffer, nextra):
    """Create a 1-liner summary message for a backup comparison.

    backup = filename of the backup copy
    master = filename of the master copy that the backup was compared with
    nmissing = # of files in master that are missing from backup
    ndiffer = # of files that have different timestamp or size from master
    nextra = # of files in backup that are not in master

    Returns a string that describes/summarizes the results of the comparison.
    """
    clauses = []
    if nmissing > 0:
        clauses.append('{0} missing file'.format(nmissing) +
                       ('s' if nmissing > 1 else ''))
    if ndiffer > 0:
        clauses.append('{0} different timestamp/size'.format(ndiffer))
    if nextra > 0:
        clauses.append('{0} extra file'.format(nextra) +
                       ('s' if nextra > 1 else ''))

    if nmissing == 0 and ndiffer == 0 and nextra == 0:
        return os.path.splitext(backup)[0] + ' -- clean backup, all files match ' + master
    else:
        return os.path.splitext(backup)[0] + ' -- ' + ', '.join(clauses)

#-------------------------------------------------------------------------------
def ts_to_datetime(linetext):
    """Convert a directory listing timestamp (as displayed by Windows DIR, for
    example "12/08/2016  02:33 PM") to a datetime value.

    NOTE: these values don't include the seconds portion of the timestamp.
    This is not a problem for the original use of this function, but could be
    an issue if this code is used elsewhere.
    """
    windows_timestamp = linetext[:20]
    return datetime.datetime.strptime(windows_timestamp, "%m/%d/%Y %I:%M %p")

#-------------------------------------------------------------------------------
if __name__ == '__main__':

    # switch console output to utf8 encoding, so that we don't crash on
    # display of filenames with non-ASCII characters. Note that this should
    # only be done ONCE - if it's done a second time, "ERRNO 9" errors
    # occur on print() statements. (Why?)
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

    # generate a diference report for a set of .CSV or .DIR files passed as
    # command line arguments
    #diff_report(sys.argv[1:])

    diff_report(['master.dir', 'drive2.dir', 'drive3.dir', 'drive4.dir'])
    #diff_report(['master.csv', 'drive2.csv', 'drive3.csv', 'drive4.csv'])

    # this enables command-line usage for converting a .dir to .csv
    #if len(sys.argv) == 3:
    #    INPUT_FILE = sys.argv[1]
    #    OUTPUT_FILE = sys.argv[2]
    #    print('Input file: ' + INPUT_FILE)
    #    print('Output file: ' + OUTPUT_FILE)
    #    convert_to_csv(infile=INPUT_FILE, outfile=OUTPUT_FILE)
    #else:
    #    print('Wrong number of arguments. Syntax = '+ \
    #        'python backup_verifier.py infile.dir outfile.csv')
