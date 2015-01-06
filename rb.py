#!/usr/bin/env python
# Renova Backup
# -------------
# By Fabricio Kury -- fabriciokury@gmail.com -- github.com/fabkury
# Coding start: Somewhere around april/2014.
# -
# Description:
# A very small file move and versioning utility. The intended use case
# for this program is to continuously watch for and move incremental
# backups from an unprotected folder to a protected folder, and
# maintain versions of those files in that protected folder, replacing
# old ones with newer versions whenever necessary.
# This program was designed to:
# 1) Be as efficient as possible by using the UNIX shell to move
# (rename) the files instead of copying them, and use rsync if moving
# was not possible. This means that the file operations inside one
# same filesystem will be very efficient.
# 2) Be as lightweight as possible, in order to run on restricted UNIX
# environments such as NAS CPUs, and in Python version 2.5.
#
# Default configuration (backup versions):
# 1-14 days old
# 2-3 weeks old
# 1-5 months old
# older than 6 months
#
# Command line usage:
# -u: Process all folders now (kill -USR1)
# -r: Create report now (kill -USR2)
#
# TO DOs:
# - Make a more configurable scheduling system.
# - Read all configurations from a file. Separate the code from the local configurations.
# - Make the code produce the S99rbd and Painel.php files.
# - Make the system also move files lingering in the RB_SOURCE folder?

from __future__ import with_statement
import subprocess
import os, sys
import datetime, time
import signal

#
## Configurations -- these directories need to be changed also in S99rbd and Painel.php.
RB_SOURCE = '/shares/mirzakury/Renova/Backup/Temp/'
RB_DESTINATION = '/shares/fabriciokury/Arquivo/SG/RB/'

#
## Constants (or near-constants... I admit I got a big messed in this)
RB_CMD_CHECK_FOLDERS = 1
RB_REGISTERED_PROCESS_ID = ''
RB_PROCESS_ID_FILE = os.path.realpath(__file__) + '.pidf'
RB_FILE_LAST_SYNC = os.path.realpath(__file__) + '.lsf'
RB_FILE_REPORT = os.path.dirname(os.path.abspath(__file__)) + '/' + 'relatorio.html'
RB_FILETIME_EQUAL_REANGE = 10 # 10 seconds
RB_DATE_VERBOSE_FORMAT = '%Y-%m-%d %Hh%Mm%Ss'
RB_SYNC_INTERVAL_IN_HOURS = 4 # One sync per 4 hours
RB_SYNC_INTERVAL_DELTA = 1 # Number of hours to offset (add) the sync interval deadline
RB_SLEEP_RESOLUTION = 10000 # Best if not a multiple of the number of seconds in a day
RB_SLEEP_SAFETY_MIN = 10 # This is the minimum sleep in any call to time.sleep(). This is good to minimize the impact of unpredicted bugs.
RB_SYSTEM_STATE_VERBOSE = ['Aguardando tarefas futuras', 'Executando sincronizacao']
RB_SS_SLEEPING = 0
RB_SS_SYNCING = 1
DT_1_DAY = 60*60*24
DT_1_WEEK = DT_1_DAY*7
DT_2_WEEKS = DT_1_WEEK*2
DT_26_WEEKS = DT_1_WEEK*26

#
## Globals
g_commands = []
g_system_state = RB_SS_SLEEPING
g_last_sync = 0
g_next_sync = 0

#
## Functions
def make_folder_name_from_time(timestamp):
    dt = time.time() - timestamp
    if dt >= DT_26_WEEKS:
        return 'Semestre'
    month_name = ['0', 'janeiro', 'fevereiro', 'marco', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
    day_name = ['0', 'segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado', 'domingo']
    timestamp_datetime = datetime.datetime.fromtimestamp(timestamp)
    if dt < DT_2_WEEKS:
        if dt < DT_1_DAY:
            return 'Ha menos de 24 horas'
        return ('%04d' % timestamp_datetime.year) + '-' + ('%02d' % timestamp_datetime.month) + '-' + ('%02d' % timestamp_datetime.day) + ' (' + day_name[timestamp_datetime.isoweekday()] + ')'
    return ('%04d' % timestamp_datetime.year) + '-' + ('%02d' % timestamp_datetime.month) + ' (' + month_name[timestamp_datetime.month] + ')'

def this_process_is_second_instance():
    out, err = subprocess.Popen(['head', '/proc/' + str(RB_REGISTERED_PROCESS_ID) + '/cmdline'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    if __file__ in out and 'python' in out:
        return True
    return False

def rm_empty_dirs(dir, delete_root=True):
    for dirpath, _, _ in os.walk(dir, topdown=False):  # Listing the files
        if not delete_root and dirpath == dir:
            continue
        try:
            os.rmdir(dirpath)
        except OSError:
            pass
    return not os.path.exists(dir)

def filetime(f): # Modify this function to modify which time is considered by the program (modification, access or creation).
    # Use mtime (modification time) because *nix systems don't store cration time.
    return int(os.stat(f).st_mtime)

def compare_filetime(fa, fb): # Used to sort the file list.
    return int(filetime(fa) - filetime(fb))

def read_rbpif():
    global RB_REGISTERED_PROCESS_ID
    try:
        with open(RB_PROCESS_ID_FILE, 'r') as file_in:
            RB_REGISTERED_PROCESS_ID = int(file_in.read())
    except:
        pass
    
def write_rbpif():
    global RB_REGISTERED_PROCESS_ID
    RB_REGISTERED_PROCESS_ID = os.getpid()
    with open(RB_PROCESS_ID_FILE, 'w') as file_out:
        file_out.write(str(RB_REGISTERED_PROCESS_ID))

def read_rbls():
    global g_last_sync
    try:
        with open(RB_FILE_LAST_SYNC, 'r') as file_in:
            g_last_sync = float(file_in.read())
            return True
    except:
        pass
    return False # False means error

def write_rbls(ls_time):
    global g_last_sync
    with open(RB_FILE_LAST_SYNC, 'w') as file_out:
        file_out.write(str(ls_time))
    g_last_sync = ls_time

def update_next_sync_time():
    global g_next_sync, RB_CURRENT_SLEEP
    ts_dt = datetime.datetime.fromtimestamp(g_last_sync)
    ts_dt = ts_dt.replace(minute=0, second=0, microsecond=0)
    ts_dt = ts_dt.replace(hour=ts_dt.hour-(ts_dt.hour%RB_SYNC_INTERVAL_IN_HOURS))
    ts_dt += datetime.timedelta(hours=RB_SYNC_INTERVAL_IN_HOURS)
    ts_dt += datetime.timedelta(hours=RB_SYNC_INTERVAL_DELTA)    
    g_next_sync = time.mktime(ts_dt.timetuple())
    RB_CURRENT_SLEEP = min(RB_SLEEP_RESOLUTION, max(g_next_sync-time.time(), RB_SLEEP_SAFETY_MIN))

def process_folder(source, target):
    pre_process_time = filetime(source) # Save the old time
    if not os.path.exists(os.path.dirname(target)):
        try:
            os.makedirs(os.path.dirname(target));
        except:
            return
    if not os.path.exists(target):
        subprocess.call('mv "'+source+'" "'+target+'"', shell=True)
    if os.path.isdir(source):
        for dir in os.listdir(source):
            process_folder(os.path.join(source, dir), os.path.join(target, dir))
        if os.listdir(source):
            subprocess.call('rsync -vtru --progress --remove-sent-files --iconv=utf8 "' + source + '/" "' + target + '"', shell=True)
            try:
                os.rmdir(source)
            except:
                pass
    try:
        os.utime(target, (time.time(), pre_process_time)) # Write the old time back.
    except:
        pass
    return rm_empty_dirs(source)
    
def scan_watched_folders(source = RB_SOURCE, dest = RB_DESTINATION):
    if not os.path.isdir(source):
        print 'Source directory not found.'
        return
    source_dir = sorted([source + dir for dir in os.listdir(source)], cmp=compare_filetime)
    for i in xrange(len(source_dir)-1, -1, -1): # Start from the oldest     
        if not os.path.isdir(source_dir[i]):
            continue
        destination_dir = RB_DESTINATION + make_folder_name_from_time(filetime(source_dir[i]))
        if source_dir[i] != destination_dir:
            print 'Processing "' + source_dir[i] + '" to "' + destination_dir + '".'
            process_folder(source_dir[i], destination_dir)
       
def create_report(dest = RB_FILE_REPORT):
    print 'Writing system status report to "' + dest + '".'
    with open(dest, 'w') as file_out:
        file_out.write('<html>\n<head>\n<title>Renova Backup - Relatorio</title>\n</head>\n<body>\n')
        file_out.write('<h1>Renova Backup v1.0</h1>\n<span style="font-size:18pt;">\n')
        global g_system_state, g_last_sync
        global RB_CURRENT_SLEEP, RB_SYNC_INTERVAL_IN_HOURS, RB_SYNC_INTERVAL_DELTA, RB_SYSTEM_STATE_VERBOSE
        file_out.write('<p>Estado do sistema: ' + RB_SYSTEM_STATE_VERBOSE[g_system_state] + '.</p>\n')
        file_out.write('<p>Relatorio gerado em: ' + datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %Hh%Mm%Ss') + '.</p>\n')
        file_out.write('<p>Ultima sincronizacao: ' + datetime.datetime.fromtimestamp(g_last_sync).strftime('%Y-%m-%d %Hh%Mm%Ss') + '.</p>\n')
        file_out.write('<p>Proxima sincronizacao: ' + datetime.datetime.fromtimestamp(g_next_sync).strftime('%Y-%m-%d %Hh%Mm%Ss') + '.</p>\n')
        file_out.write('<p>Dormindo para proxima sincronizacao: ' + ('%d' % RB_CURRENT_SLEEP) + ' segundos.</p>\n')
        file_out.write('<p>A sincronizacao e feita diariamente as:')
        for i in range((24-(24%RB_SYNC_INTERVAL_IN_HOURS))/RB_SYNC_INTERVAL_IN_HOURS):
            file_out.write(' %02d' % (i*RB_SYNC_INTERVAL_IN_HOURS + RB_SYNC_INTERVAL_DELTA))
        file_out.write(' horas.</p>\n')
        file_out.write('</span>\n</body>\n</html>')
    
def receive_USR1(signum, stack):
    global g_commands
    print 'USR1 received. Checking folders now.'
    g_commands.append(RB_CMD_CHECK_FOLDERS)
	
def receive_USR2(signum, stack):
    print 'USR2 received. Creating report now.'
    create_report()

#
## Begin program execution here.
print 'Renova Backup v0.5.'
print 'By Fabricio Kury -- fabriciokury@gmail.com -- github.com/fabkury'
print ''

# Prevent running two instances of this same script.
read_rbpif()
if this_process_is_second_instance():
    print 'Process ' + str(RB_REGISTERED_PROCESS_ID) + ' found active. This process is second instance.'
    if len(sys.argv) > 1:
        print 'Sending signal to process ' + str(RB_REGISTERED_PROCESS_ID) + ': ' + sys.argv[1]
        if sys.argv[1] == '-u':
            os.kill(RB_REGISTERED_PROCESS_ID, signal.SIGUSR1)
        elif sys.argv[1] == '-r':
            os.kill(RB_REGISTERED_PROCESS_ID, signal.SIGUSR2)
    print 'Exitting now.'
    os._exit(0)
write_rbpif()

# Read last sync and calculate the next one.
read_rbls()
update_next_sync_time()

# Write down system status and set up the signal listeners.
create_report()
signal.signal(signal.SIGUSR1, receive_USR1)
signal.signal(signal.SIGUSR2, receive_USR2)

# Enter program loop.
while True:
    print 'Enter loop on process ' + str(RB_REGISTERED_PROCESS_ID) + '.'
    if time.time() > g_next_sync:
        g_commands.append(RB_CMD_CHECK_FOLDERS)
    for cmd in g_commands[:]:
        if cmd == RB_CMD_CHECK_FOLDERS:
            print 'Folder check started on ' + datetime.datetime.fromtimestamp(time.time()).strftime(RB_DATE_VERBOSE_FORMAT) + '.'
            old_system_state = g_system_state
            g_system_state = RB_SS_SYNCING
            write_rbls(time.time())
            create_report()
            if os.path.exists(RB_DESTINATION):
                print 'Scanning "'+RB_DESTINATION+'".'
                scan_watched_folders(RB_DESTINATION)
            if not RB_SOURCE == RB_DESTINATION:
                print 'Scanning "'+RB_SOURCE+'".'
                scan_watched_folders(RB_SOURCE)
            write_rbls(time.time())
            update_next_sync_time()
            g_system_state = old_system_state
            create_report()
            print 'Folder check completed on ' + datetime.datetime.fromtimestamp(time.time()).strftime(RB_DATE_VERBOSE_FORMAT) + '.'
        g_commands.remove(cmd)
    print 'Current time is ' + datetime.datetime.fromtimestamp(time.time()).strftime(RB_DATE_VERBOSE_FORMAT) + '.'
    print 'Next sync is at ' + datetime.datetime.fromtimestamp(g_next_sync).strftime(RB_DATE_VERBOSE_FORMAT) + '.'
    print 'Sleeping now: ' + str(int(RB_CURRENT_SLEEP)) + ' seconds.'
    time.sleep(RB_CURRENT_SLEEP)
