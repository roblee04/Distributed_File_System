# File: metrics.py
# Purpose:
#   Print performance measurements for our DFS

import time
import threading

from client import dfs

##############################################################################
# Invariants
# Number of times to average out each operation's RTT over
TOTAL_SAMPLES_TO_AVERAGE_OPERATIONS_OVER = 10

# Number of clients we want to test accessing the system concurrently with
NUMBER_OF_CONCURRENT_CLIENTS_TO_RUN = 10

# Mutex to syncronize printing several lines at once in a single thread
PRINTER_LOCK = threading.Lock()


##############################################################################
# Helper Functions
def ms_str(seconds: float):
  return str(round(seconds*1000,3))


def time_operation(operation_name: str, operation_fn, *args):
  start = time.time()
  try:
    operation_fn(*args)
  except Exception as err_msg:
    print('\nerror> Error executing '+operation_name+': '+str(err_msg)+'\n')
  return time.time()-start


def profile_RTT(operation_name: str, operation_fn, *args):
  total = 0
  for i in range(TOTAL_SAMPLES_TO_AVERAGE_OPERATIONS_OVER):
    total_time = time_operation(operation_name,operation_fn,*args)
    total += total_time
  rtt = total/TOTAL_SAMPLES_TO_AVERAGE_OPERATIONS_OVER
  print('> Profile took '+ms_str(rtt)+'ms to '+operation_name+ ' with: '+', '.join(args))
  return rtt


def profile_destructive_RTT(operation_name: str, operation_fn, *args):
  total = 0
  for i in range(TOTAL_SAMPLES_TO_AVERAGE_OPERATIONS_OVER):
    dfs.write(args[0],'sentinel data.') # create the file to be deleted
    if len(args) == 2 and dfs.exists(args[1]):
      dfs.delete(args[1])
    total_time = time_operation(operation_name,operation_fn,*args)
    total += total_time
  rtt = total/TOTAL_SAMPLES_TO_AVERAGE_OPERATIONS_OVER
  print('> Profile took '+ms_str(rtt)+'ms to '+operation_name+ ' with: '+', '.join(args))
  return rtt


##############################################################################
# Profile RTT for a Single Client
# Creates up to 3 files in the UVM at once.
def profile_single_client():
  THREAD_ID = threading.get_ident()
  FILE_PREFIX = str(THREAD_ID)+'-'
  dfs.write(FILE_PREFIX+'BASEFILE.md','This basefile is used to conduct performance analytics. Will be deleted.')
  read = profile_RTT('read',dfs.read,FILE_PREFIX+'BASEFILE.md')
  write = profile_RTT('write',dfs.write,FILE_PREFIX+'file.txt','some contents. nothing crazy, but enough to require at least a bit of IO.')
  delete = profile_destructive_RTT('delete',dfs.delete,FILE_PREFIX+'file.txt')
  copy = profile_RTT('copy',dfs.copy,FILE_PREFIX+'BASEFILE.md',FILE_PREFIX+'BASEFILE-copy.md')
  dfs.delete(FILE_PREFIX+'BASEFILE-copy.md') # delete copy
  rename = profile_destructive_RTT('rename',dfs.rename,FILE_PREFIX+'file.txt',FILE_PREFIX+'renamed-file.txt')
  dfs.delete(FILE_PREFIX+'renamed-file.txt') # delete renamed file
  exists = profile_RTT('exists',dfs.exists,FILE_PREFIX+'BASEFILE.md')
  dfs.delete(FILE_PREFIX+'BASEFILE.md')
  with PRINTER_LOCK:
    print('\n**********************************************************')
    print('> Running client ID='+str(THREAD_ID)+'; RTT averages over '+str(TOTAL_SAMPLES_TO_AVERAGE_OPERATIONS_OVER)+' runs:')
    print('  -> read: '+ms_str(read)+'ms')
    print('  -> write: '+ms_str(write)+'ms')
    print('  -> delete: '+ms_str(delete)+'ms')
    print('  -> copy: '+ms_str(copy)+'ms')
    print('  -> rename: '+ms_str(rename)+'ms')
    print('  -> exists: '+ms_str(exists)+'ms')
    print('**********************************************************\n')
  return [read, write, delete, copy, rename, exists]


##############################################################################
# Profile RTT for Multiple Clients
CLIENT_RESULTS_LIST = []
CLIENT_RESULTS_LIST_LOCK = threading.Lock()

def total_results():
  with CLIENT_RESULTS_LIST_LOCK:
    return len(CLIENT_RESULTS_LIST)


def run_client():
  result = profile_single_client()
  with CLIENT_RESULTS_LIST_LOCK:
    CLIENT_RESULTS_LIST.append(result)


def profile_multiple_clients():
  global CLIENT_RESULTS_LIST
  CLIENT_RESULTS_LIST = []
  for _ in range(NUMBER_OF_CONCURRENT_CLIENTS_TO_RUN):
    threading.Thread(target=run_client).start()
  while total_results() < NUMBER_OF_CONCURRENT_CLIENTS_TO_RUN:
    time.sleep(0.5)
  read = sum([run[0] for run in CLIENT_RESULTS_LIST])/len(CLIENT_RESULTS_LIST)
  write = sum([run[1] for run in CLIENT_RESULTS_LIST])/len(CLIENT_RESULTS_LIST)
  delete = sum([run[2] for run in CLIENT_RESULTS_LIST])/len(CLIENT_RESULTS_LIST)
  copy = sum([run[3] for run in CLIENT_RESULTS_LIST])/len(CLIENT_RESULTS_LIST)
  rename = sum([run[4] for run in CLIENT_RESULTS_LIST])/len(CLIENT_RESULTS_LIST)
  exists = sum([run[5] for run in CLIENT_RESULTS_LIST])/len(CLIENT_RESULTS_LIST)
  with PRINTER_LOCK:
    print('\n**********************************************************')
    print('> Running '+str(NUMBER_OF_CONCURRENT_CLIENTS_TO_RUN)+' clients; RTT averages over '+str(TOTAL_SAMPLES_TO_AVERAGE_OPERATIONS_OVER)+' runs:')
    print('  -> read: '+ms_str(read)+'ms')
    print('  -> write: '+ms_str(write)+'ms')
    print('  -> delete: '+ms_str(delete)+'ms')
    print('  -> copy: '+ms_str(copy)+'ms')
    print('  -> rename: '+ms_str(rename)+'ms')
    print('  -> exists: '+ms_str(exists)+'ms')
    print('**********************************************************\n')


##############################################################################
# Profile Allocating a new UVM
def total_files_possibly_created():
  return 3 * NUMBER_OF_CONCURRENT_CLIENTS_TO_RUN


def profile_UVM_allocation():
  global TOTAL_SAMPLES_TO_AVERAGE_OPERATIONS_OVER
  old = TOTAL_SAMPLES_TO_AVERAGE_OPERATIONS_OVER
  TOTAL_SAMPLES_TO_AVERAGE_OPERATIONS_OVER = 1
  n = total_files_possibly_created()
  for i in range(n):
    dfs.write('file-'+str(i),'random data #'+str(i)) # flood first UVM
  rtt = profile_RTT('UVM Allocation',dfs.write,'file-'+str(n),'random data #'+str(n))
  for i in range(n+1):
    dfs.delete('file-'+str(i))
  with PRINTER_LOCK:
    print('\n**********************************************************')
    print('> Allocating a UVM took '+ms_str(rtt)+'ms!')
    print('**********************************************************\n')
  TOTAL_SAMPLES_TO_AVERAGE_OPERATIONS_OVER = old


##############################################################################
# Main Execution
def main():
  global NUMBER_OF_CONCURRENT_CLIENTS_TO_RUN
  print('\n>> IMPORTANT: Make sure your UVMs have <UVM_MAXIMUM_NUMBER_OF_FILES = '+str(total_files_possibly_created())+'>!')
  print('   * Otherwise won\'t have enough disk for our concurrent client requests!')
  print('\n>> IMPORTANT: Assumes enough pooled RVMs to allocate a new UVM/RVM unit!')
  print('\n===============================================================================')
  print('Profiling Executing 1 Client:')
  print('===============================================================================\n')
  # > Running client ID=8673235520; RTT averages over 10 runs:
  # -> read: 26.167ms
  # -> write: 43.131ms
  # -> delete: 41.901ms
  # -> copy: 42.146ms
  # -> rename: 43.987ms
  # -> exists: 28.763ms
  profile_single_client()
  NUMBER_OF_CONCURRENT_CLIENTS_TO_RUN = int(NUMBER_OF_CONCURRENT_CLIENTS_TO_RUN/2)
  print('\n\n===============================================================================')
  print('Profiling Executing '+str(NUMBER_OF_CONCURRENT_CLIENTS_TO_RUN)+' Clients:')
  print('===============================================================================\n')
  # > Running 5 clients; RTT averages over 10 runs:
  # -> read: 30.296ms
  # -> write: 50.776ms
  # -> delete: 46.6ms
  # -> copy: 46.168ms
  # -> rename: 47.281ms
  # -> exists: 30.63ms
  profile_multiple_clients()
  NUMBER_OF_CONCURRENT_CLIENTS_TO_RUN *= 2
  print('\n\n===============================================================================')
  print('Profiling Executing '+str(NUMBER_OF_CONCURRENT_CLIENTS_TO_RUN)+' Clients:')
  print('===============================================================================\n')
  # > Running 10 clients; RTT averages over 10 runs:
  # -> read: 63.979ms
  # -> write: 83.777ms
  # -> delete: 84.565ms
  # -> copy: 91.063ms
  # -> rename: 77.709ms
  # -> exists: 61.922ms
  profile_multiple_clients()
  print('\n\n===============================================================================')
  print('Profiling Allocating a New UVM:')
  print('===============================================================================\n')
  # > Allocating a UVM took 8284.931ms!
  profile_UVM_allocation()

  # Time to launch a new RVM, observed as: 0.523s
  # Time to launch a new RVM leader, observed as: 3.259s
  # Time to replace a UVM, observed as: 0.943s


main()
