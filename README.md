NephoScale CloudBench Utility
=============================

This utility is used to collect and record important performance metrics 
surrounding system CPU and storage performance.  

The goal with this utility is to distill several benchmarking utilities
results such as phoronix, fio, ioping, and iozone into simple results
that can be easily compared between cloud providers.

## Requirements ##
* Ubuntu Precise 14.04
* Python 2.7+

## How to use ##

To run this utility and install all dependencies simply run the following:

```
$ curl https://raw.githubusercontent.com/nephoscale/cloudbench/master/run.sh | bash
```

or you can clone this repository and run it:

```
$ ./bench.py --deps
````

The ```deps``` flag will ensure that all depenencies are installed prior to running tests.

### Test Results ###

The test results will be written to syslog as well as /tmp/cloudbench.csv

### IO Test Types ####

There are two IO test types available.  It is recommend you run the benchmark script
with the defaults which will attempt to test using a small amount of data using 
DIRECT I/O.  Some environments will not support this reliably, so you can run 
the benchmarks with ```--iobench_type=long``` to ensure the amount of data written
is twice that of the system RAM to avoid contaminated results from buffering.

## Example Output ##

Example Output Below

```
$ ./bench.py -d --deps
2014-08-03 21:21:23,084 cloudbench   INFO     Installing Dependencies
2014-08-03 21:21:23,084 cloudbench   INFO     Installing package php5-cli
2014-08-03 21:21:24,635 cloudbench   INFO     Installing package php5-gd
2014-08-03 21:21:25,131 cloudbench   INFO     Installing package php5-json
2014-08-03 21:21:25,616 cloudbench   INFO     Installing package sqlite3
2014-08-03 21:21:26,098 cloudbench   INFO     Installing package iozone3
2014-08-03 21:21:26,576 cloudbench   INFO     Installing package fio
2014-08-03 21:21:27,056 cloudbench   INFO     Installing package wget
2014-08-03 21:21:27,533 cloudbench   INFO     Installing package ioping
2014-08-03 21:21:28,066 cloudbench   INFO     Fetching and installing phoronix test suite
2014-08-03 21:21:35,821 cloudbench   INFO     Beginning CloudBench tests
2014-08-03 21:21:35,822 cloudbench   INFO     Installing phoronix test Multicore Kernel Compile (seconds)
2014-08-03 21:21:37,713 cloudbench   INFO     Running phoronix test Multicore Kernel Compile (seconds)
2014-08-03 21:28:57,145 cloudbench   INFO     Running 16k record size IOZone Direct I/O bandwidth test
2014-08-03 21:29:15,048 cloudbench   INFO     Write 126 MB/s Read 125 MB/s
2014-08-03 21:29:15,048 cloudbench   INFO     Running test FIO random writes using 8k blocks
2014-08-03 21:36:24,413 cloudbench   INFO     Test results for FIO random writes using 8k blocks: 305 IOPS
2014-08-03 21:36:24,413 cloudbench   INFO     Running test FIO random reads using 4k blocks
2014-08-03 21:47:40,685 cloudbench   INFO     Test results for FIO random reads using 4k blocks: 193 IOPS
2014-08-03 21:47:40,685 cloudbench   INFO     Running IOPing write latency tests
2014-08-03 21:47:42,802 cloudbench   INFO     IOPing write latency 6467usec
2014-08-03 21:47:42,802 cloudbench   INFO     All CloudBench tests completed
```

Results stored in /tmp/cloudbench.csv

```
$ cat /tmp/cloudbench.csv 
hostname,test_name,test_description,test_result
hpdesktop,iozone,IOZone I/O Throughput Test,Write 126 MB/s Read 125 MB/s
hpdesktop,random-read,FIO random reads using 4k blocks,193 IOPS
hpdesktop,ioping,IOPing Write Latency Test,6467usec
hpdesktop,pts/build-linux-kernel,Multicore Kernel Compile (seconds),80
hpdesktop,random-write,FIO random writes using 8k blocks,305 IOPS
```
