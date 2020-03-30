# Network
import urllib.request, urllib.parse, urllib.error
import http.cookiejar

# Concurrency
import threading
import queue
import itertools

import pycurl

# Etc
import time
from colorama import Fore, Back, Style

# Global variables
#in_filename  = 'input/3.txt'
in_directory = './input/'
out_filename = 'output/out_filtered.txt'
test_url = 'http://www.google.com/humans.txt'
thread_number = 500
timeout_value = 1

good_message = Fore.GREEN + "GOOD!  " + Fore.RESET
bad_message = Fore.RED + "BAD " + Fore.RESET

# Stats
good_proxy_num = itertools.count()
start_time = time.time()
end_time   = time.time()

# Safe print()
mylock = threading.Lock()
def sprint(*a, **b):
    with mylock:
        print(*a, **b)


#
# Printer
#
class PrintThread(threading.Thread):
    def __init__(self, queue, filename):
        threading.Thread.__init__(self)
        self.queue = queue
        self.output = open(filename, 'a')
        self.shutdown = False

    def write(self, line):
        print(line, file=self.output)

    def run(self):
        while not self.shutdown:
            lines = self.queue.get()
            self.write(lines)
            self.queue.task_done()

    def terminate(self):
        self.output.close()
        self.shutdown = True



#
# Processor
#
class ProcessThread(threading.Thread):
    def __init__(self, id, task_queue, out_queue):
        threading.Thread.__init__(self)
        self.task_queue = task_queue
        self.out_queue  = out_queue
        self.id = id

    # ...
    def run(self):
        while True:
            task   = self.task_queue.get()
            result = self.process(task)

            if result is not None:
                self.out_queue.put(result)
                next(good_proxy_num)

            self.task_queue.task_done()


    # Do the processing job here
    def process(self, task):
        proxy = task
        log_msg = str("Thread #%3d.  Trying HTTP proxy %21s \t\t" % (self.id, proxy))
        c1 = pycurl.Curl()
        c1.setopt(pycurl.URL, test_url)
        c1.setopt(pycurl.PROXY, proxy.split(':')[0])
        c1.setopt(pycurl.PROXYPORT, int(proxy.split(':')[1]))
        c1.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5)
        c1.setopt(pycurl.CONNECTTIMEOUT, self.timeout_value)
        try:
            t1 = time.time()
            response = c1.perform()
            t2 = time.time()
        except Exception as e:
            log_msg += "%s (%s)" % (bad_message, str(e))
            sprint(log_msg)
            return None

        log_msg += good_message + " Response time: %d, response code=%s" % ( int((t2-t1)*1000), c1.getinfo(pycurl.HTTP_CODE) )
        sprint(log_msg)
        return proxy

    def terminate(self):
        None
        #print("Thread #%d is down..." % (self.id))

#
# Main starts here
#
# Init some stuff
input_queue  = queue.Queue()
result_queue = queue.Queue()


# Spawn worker threads
workers = []
for i in range(0, thread_number):
    t = ProcessThread(i, input_queue, result_queue)
    t.setDaemon(True)
    t.start()
    workers.append(t)

# Spawn printer thread to print
f_printer = PrintThread(result_queue, out_filename)
f_printer.setDaemon(True)
f_printer.start()

# Add some stuff to the input queue
start_time = time.time()

proxy_list = []
import os
for root, dirs, files in os.walk(in_directory):
    for file in files:
        if file.endswith(".txt"):
            # read all lines from file
            file_line_list = [line.rstrip('\n') for line in open(os.path.join(root, file), 'r')]
            # append to proxy_list
            proxy_list.extend(file_line_list)

for proxy in proxy_list:
    input_queue.put(proxy)

total_proxy_num = len(proxy_list)
print("got %d proxies to check" % total_proxy_num)

if total_proxy_num == 0:
    exit()

# Wait for queue to get empty
input_queue.join()
result_queue.join()


#while (not input_queue.empty()):
#    time.sleep(1)


# Shutdown
f_printer.terminate()

for worker in workers:
    worker.terminate()

# Print some info
good_proxy_num = float(next(good_proxy_num))
print("In: %d. Good: %d, that's %.2f%%" % (total_proxy_num, good_proxy_num, 100.0 * good_proxy_num/total_proxy_num))

end_time = time.time()
print("Time elapsed: %.1f seconds." % (end_time - start_time))
print("Bye-bye!")