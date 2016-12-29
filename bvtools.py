"""bvtools.py
Tools for backup verification.

These utilities are used to analyze a set of backup drives and identify any
extra, missing, or modified files.
"""
import csv
import datetime
import sys

#-------------------------------------------------------------------------------
def add_quotes(fieldvalue):
    """Add quotes to a string if it contains a comma.
    """
    return '"' + fieldvalue + '"' if ',' in fieldvalue else fieldvalue

#-------------------------------------------------------------------------------
def convert_to_csv(infile=None, outfile=None, path=None):
    """Parse a text file containing a Windows directory listing and write the
    data to a CSV file.

    infile = a file captured with a command such as DIR *.* /S >filename.dir
    outfile = name of a CSV file to be written
    path = a string indicating the root path of the backup structure, so that
           this can be removed from all data in the output file. For example,
           if the input .dir file was created with a "DIR d:\" command, then
           the path argument would be "d:\"
    """
    if not infile or not outfile or not path:
        return # nothing to do

    # switch console output to utf8 encoding, so that we don't crash on
    # display of filenames with non-ASCII characters ...
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

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

        datarow = add_quotes(current_folder) + ',' + add_quotes(filename) + ',' + \
            str(timestamp) + ',' + str(filesize)

        fhandle.write(datarow + '\n')
        lines_written += 1
        if lines_written % 10000 == 0:
            print('{} lines written to '.format(lines_written) + outfile)

    # close file, summarize
    fhandle.close()
    print('{} lines written to '.format(lines_written) + outfile)

#-------------------------------------------------------------------------------
def diff_report(csvfiles=None):
    """Generate a difference analysis for a list of CSV files. The CSV files
    should be as created by convert_to_csv, and the first file in the list is
    considered the "master" copy for analysis purposes. Output is displayed to
    the console, can be captured to a text file as needed.
    """
    if not csvfiles:
        # if no CSV files were specified, use our current defaults
        csvfiles = ['master.csv', 'drive1.csv', 'drive2.csv', 'drive3.csv']

    print('-'*80)
    for nbackup, filename in enumerate(csvfiles):
        print('MASTER reference copy:  ' if nbackup == 0 else 'Backup copy to compare: ', end='')
        print(filename)
    print('-'*80)

    # master_dict = a dictionary created from the master backup (first file)
    #    key = folder + r'\' + filename
    #    value = timestamp + filesize
    master_dict = {}
    for row in csv.reader(open(csvfiles[0], newline=''), delimiter=',', quotechar='"'):
        master_dict[row[0] + '\\' + row[1]] = row[2] + str(row[3])

    summaries = [] # list of 1-liner summaries to be displayed at end

    # compare each backup against the master
    for nbackup, filename in enumerate(csvfiles):
        if nbackup == 0:
            continue # skip the master
        nmissing = 0
        ndiffer = 0
        nextra = 0
        print('comparing ' + filename + ' to master ...')
        backup_dict = {} # dictionary of this backup, populated in loop below
        # scan through this backup and compare each file to master dictionary ...
        for row in csv.reader(open(filename, newline=''), delimiter=',', quotechar='"'):
            fullpath = row[0] + '\\' + row[1]
            ts_size = row[2] + row[3]
            backup_dict[fullpath] = ts_size
            if fullpath in master_dict:
                if master_dict[fullpath] != ts_size:
                    print(filename.upper() + ' differs from master: ' + fullpath)
                    ndiffer += 1
            else:
                print(filename.upper() + ' missing from master: ' + fullpath)
                nextra += 1

        # scan through master_dict to identify any files missing from the backup ...
        for fullpath in master_dict:
            if fullpath not in backup_dict:
                print('MASTER, but missing from ' + filename.upper() + ': ' + fullpath)
                nmissing += 1

        print('-'*80)
        if nmissing == 0 and ndiffer == 0 and nextra == 0:
            summaries.append(filename + ' -> clean backup, all files match ' + csvfiles[0])
        else:
            summaries.append(filename + \
                ' -> {0} missing files, {1} different timestamp/size, {2} extra files'. \
                format(nmissing, ndiffer, nextra))

    # print summary at end
    print(csvfiles[0] + ' -> MASTER copy ({:,} total files)'.format(len(master_dict)))
    for summary in summaries:
        print(summary)

#-------------------------------------------------------------------------------
def dirlisting_to_datetime(linetext):
    """Convert a directory listing timestamp (as displayed by Windows DIR, for
    example "12/08/2016  02:33 PM") to a datetime value.

    NOTE: these values don't include the seconds portion of the timestamp.
    This is not a problem for the original use of this function, but could be
    an issue if this code is used elsewhere.
    """
    windows_timestamp = linetext[:20]
    return datetime.datetime.strptime(windows_timestamp, "%m/%d/%Y %I:%M %p")

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
        timestamp = dirlisting_to_datetime(linetext)
        filesize = int(linetext[20:38].strip().replace(',', ''))
        return (None, filename, timestamp, filesize)

#-------------------------------------------------------------------------------
if __name__ == '__main__':

    # generate a diference report for a set of .CSV files containing the
    # directory listings of a set of backup drives
    diff_report()

    # this block of code enables command-line usage for converting a .dir to .csv
    #if len(sys.argv) == 4:
    #    INPUT_FILE = sys.argv[1]
    #    OUTPUT_FILE = sys.argv[2]
    #    PREFIX = sys.argv[3]
    #    print('Input file: ' + INPUT_FILE)
    #    print('Output file: ' + OUTPUT_FILE)
    #    convert_to_csv(infile=INPUT_FILE, outfile=OUTPUT_FILE, path=PREFIX)
    #else:
    #    print('Wrong number of arguments. Syntax = '+ \
    #        'python dirtocsv.py infile.dir outfile.csv "prefix-to-remove-such-as-d:"')
