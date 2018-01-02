#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from progressbar import ProgressBar
import threading
import Queue
from check_bucket import *
from constants import *
from generate_strings import *
from logger import *
from search_obj import *


def search_file(file_name, prefix_postfix_option, acronyms_only_option, scanned_buckets, start_after_value, start_after_line_num, threads, print_bucket_names, output_file, access_key, secret_key):
    """Searches through the names in the file, one by one (to save memory)"""
    #Create base search instance
    num_bucket_names = get_num_bucket_names(file_name, start_after_value, start_after_line_num, prefix_postfix_option, acronyms_only_option)
    search = SearchNames(bucket_names=[], num_buckets=num_bucket_names, threads=threads, print_bucket_names=print_bucket_names, output_file=output_file, access_key=access_key, secret_key=secret_key)

    found_start = True
    if start_after_line_num or start_after_value:
        found_start = False

    f = open(file_name, "r")
    for index, line in enumerate(f):
        line = line.strip()
        if not found_start:
            if start_after_line_num == (index + 1) or start_after_value == line:
                found_start = True
            continue
        else:
            if line and not any(scanned_bucket.strip() == line.strip() for scanned_bucket in scanned_buckets):
                search.bucket_names = get_string_variations(line, prefix_postfix_option, acronyms_only_option)
                start_search(search)
                while search.bucket_names:
                    time.sleep(.5)
            else:
                print "Already scanned {line}".format(line=line)
                #Subtract the number of items skipped, to be sure #/sec isn't changed.
                search.progress.total_items -= len(get_string_variations(line, prefix_postfix_option, acronyms_only_option))
                search.progress(num_compelted=0)


def get_num_bucket_names(file_name, start_after_value, start_after_line_num, prefix_postfix_option, acronyms_only_option):
    """Calculates the number of buckets to scan, given the starting point that you want"""
    num_bucket_names = 0
    found_start = True
    if start_after_line_num or start_after_value:
        found_start = False

    f = open(file_name, "r")
    for index, line in enumerate(f):
        line = line.strip()
        if not found_start:
            if start_after_line_num == (index + 1) or start_after_value == line:
                found_start = True
            continue
        else:
            num_bucket_names += len(get_string_variations(line.strip(), prefix_postfix_option, acronyms_only_option))
    return num_bucket_names


def start_search(search):
    """Run the specified number of threads of the searcher"""
    #Make the queue of all of the threads to run
    my_queue = Queue.Queue()
    for i in range(search.threads):
        t = threading.Thread(target=search_instance, args=(search, ))
        my_queue.put(t)

    #Run all of the threads
    while not my_queue.empty():
        try:
            my_queue.get().start()
        except Exception as e:
            print "Error: %s" % (e)


def search_instance(search):
    """Run an threads of the s3 brute forcer"""
    while search.bucket_names:
        bucket_name = search.bucket_names.pop(0)       #Pops from start of array, use no param for end
        check_s3_bucket(bucket_name=bucket_name, access_key=search.access_key, secret_key=search.secret_key, output_file=search.output_file)
        
        time.sleep(sleep_sec_between_attempts)
        search.progress()
        if search.print_bucket_names:
            print bucket_name