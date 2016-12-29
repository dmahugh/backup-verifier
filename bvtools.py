"""bvtools.py
Tools for backup verification.

These utilities are used to analyze a set of backup drives and identify any
extra, missing, or modified files.

add_quotes() -------> add quotes to a string if contains commas
backup_compare() ---> compare a backup to master, return differences
convert_to_csv() ---> Parse a text file containing a Windows directory listing
diff_report() ------> Generate difference analysis for a list of CSV files
excluded_folder() --> Identify folders to be excluded (.git, etc.)
parseline() --------> Parse a line of text from a Windows directory listing
summary_msg() ------> Create a 1-liner summary message for a backup comparison
ts_to_datetime() ---> Convert Windows DIR timestamp to datetime value
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
def backup_compare(backup, master):
    """Compare a backup to a master copy, return the differences.

    backup = .CSV data file of the backup copy, with folder/filename/timestamp/size
    master = dictionary of the master, keys = filename, values = timestamp+size

    Returns (nmissing, ndiffer, nextra)
    """
    nmissing = 0
    ndiffer = 0
    nextra = 0
    print('comparing ' + backup + ' to master ...')
    backup_dict = {} # dictionary of this backup, populated in loop below
    # scan through this backup and compare each file to master dictionary ...
    for row in csv.reader(open(backup, newline=''), delimiter=',', quotechar='"'):
        fullpath = row[0] + '\\' + row[1]
        ts_size = row[2] + row[3]
        backup_dict[fullpath] = ts_size
        if fullpath in master:
            if master[fullpath] != ts_size:
                print(backup.upper() + ' differs from master: ' + fullpath)
                ndiffer += 1
        else:
            print(backup.upper() + ' missing from master: ' + fullpath)
            nextra += 1

    # scan through master_dict to identify any files missing from the backup ...
    for fullpath in master:
        if fullpath not in backup_dict:
            print('MASTER, but missing from ' + backup.upper() + ': ' + fullpath)
            nmissing += 1

    print('-'*80)
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

    # switch console output to utf8 encoding, so that we don't crash on
    # display of filenames with non-ASCII characters ...
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

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
                print('>>> PATH SET: ' + path)
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
        nmissing, ndiffer, nextra = backup_compare(filename, master_dict)
        summaries.append(summary_msg(filename, csvfiles[0], nmissing, ndiffer, nextra))

    # print summary at end
    print(csvfiles[0] + ' -> MASTER copy ({:,} total files)'.format(len(master_dict)))
    for summary in summaries:
        print(summary)

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
        clauses.append('{0} missing file'.format(nmissing) + ('s' if nmissing > 1 else ''))
    if ndiffer > 0:
        clauses.append('{0} different timestamp/size'.format(ndiffer))
    if nextra > 0:
        clauses.append('{0} extra file'.format(nextra) + ('s' if nextra > 1 else ''))

    if nmissing == 0 and ndiffer == 0 and nextra == 0:
        return backup + ' -> clean backup, all files match ' + master
    else:
        return backup + ' -> ' + ', '.join(clauses)

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

    # generate a diference report for a set of .CSV files containing the
    # directory listings of a set of backup drives
    diff_report()

    # this block of code enables command-line usage for converting a .dir to .csv
    #if len(sys.argv) == 3:
    #    INPUT_FILE = sys.argv[1]
    #    OUTPUT_FILE = sys.argv[2]
    #    print('Input file: ' + INPUT_FILE)
    #    print('Output file: ' + OUTPUT_FILE)
    #    convert_to_csv(infile=INPUT_FILE, outfile=OUTPUT_FILE)
    #else:
    #    print('Wrong number of arguments. Syntax = '+ \
    #        'python bvtools.py infile.dir outfile.csv')
