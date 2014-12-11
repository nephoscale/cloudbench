#! /usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


import logging
import os
import sys
import json
import argparse
import random
import time
import hashlib
import subprocess
import re
import socket
from os.path import expanduser
from logging.handlers import SysLogHandler

LOG = logging.getLogger('cloudbench')
LOG_FORMAT='%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
LOG_DATE = '%m-%d %H:%M'
DESCRIPTION = "NephoScale CloudBench Tool"

# define required packages (on Ubuntu 12.04+) to run tests
PACKAGES_REQUIRED = (
    'php5-cli',
    'php5-gd',
    'php5-json',
    'sqlite3',
    'iozone3',
    'fio',
    'wget',
    'ioping',
)

REQUIRED_PHORONIX_TESTS = (
    # only one result is supported in re.compile
    ('Multicore Kernel Compile (seconds)', 'pts/build-linux-kernel', re.compile('\s+Average: (\d+)\.\d+ Seconds')),
)

REQUIRED_FIO_TESTS = (
    # only one result is supported in re.compile
    # test_name, fio_hdr, fio_rw, fio_blocksize, fio_ioengine, regexp
    ('FIO random writes using 4k blocks',    'random-write', 'randwrite',    '4k',   'sync', re.compile('write.+iops=(\d+).+')),
    ('FIO random reads using 4k blocks',     'random-read',  'randread',     '4k',   False,  re.compile('read.+iops=(\d+).+')),
    # not very reliable even with Direct I/O
    # ('FIO sequential reads using 16 blocks', 'seq-read',     'read',         '16k',  False,  re.compile('read.+iops=(\d+).+'))
)

# phoronix information
PHORONIX_URL    = 'http://phoronix-test-suite.com/releases/repo/pts.debian/files/phoronix-test-suite_5.2.1_all.deb'
PHORONIX_MD5    = '8d0c9ffca7a809934419a3e3ed6e304e'
PHORONIX_TMP    = '/tmp/phoronix.deb'

# define some paths
PATH_APTGET     = '/usr/bin/apt-get'
PATH_DPKG       = '/usr/bin/dpkg'
PATH_WGET       = '/usr/bin/wget'
PATH_SUDO       = '/usr/bin/sudo'
PATH_PHORONIX   = '/usr/bin/phoronix-test-suite'

# default path where iobench files are written
IOBENCH_PATH	= '/tmp'

# where we should write results
PATH_RESULT_CSV = '/tmp/cloudbench.csv'


class CloudBenchException(BaseException):
    pass

def parse_args():

    ap = argparse.ArgumentParser(description=DESCRIPTION)
    ap.add_argument('-d', '--debug', action='store_true',
                    default=False, help='Show verbose/debugging output')
    ap.add_argument('--deps', action='store_true',
                    default=False, help='Install Dependencies')
    ap.add_argument('--iobench_type', action='store',
                    default='short', help="Type of I/O bench to do, short or long.  A long test reads and writes ram*2")
    ap.add_argument('--iobench_short_size', action='store_true',
                    default=512, help="I/O Bench (Direct I/O) Test Size")
    return ap.parse_args()

def setup_logging(args):
    level = logging.INFO
    if args.debug:
        level = logging.DEBUG
    logging.basicConfig(level=level, format=LOG_FORMAT, date_fmt=LOG_DATE)
    handler = SysLogHandler(address='/dev/log')
    syslog_formatter = logging.Formatter('%(name)s: %(levelname)s %(message)s')
    handler.setFormatter(syslog_formatter)
    LOG.addHandler(handler)

def run(args):

    if args.deps:
        LOG.info("Installing Dependencies")
        install_deps(args)

    run_tests(args)

def install_deps(args):
    """
    Install all dependencies required to run tests

    By default, we will install no new utilities unless this flag is passed

    :param args: argparse object
    """

    for pkg in PACKAGES_REQUIRED:
        LOG.info("Installing package %s", pkg)
        cmd = "%s %s install -y %s" % (PATH_SUDO, PATH_APTGET, pkg)
        LOG.debug("CMD: %s", cmd)
        subprocess.check_call(cmd, shell=True)

    # fetch phoronix debian package
    LOG.info("Fetching and installing phoronix test suite")
    cmd = PATH_WGET + ' ' + PHORONIX_URL + ' -O ' + PHORONIX_TMP
    LOG.debug("CMD: %s", cmd)
    subprocess.check_call(cmd, shell=True)

    # ensure md5 matches
    download_md5 = hashlib.md5(open(PHORONIX_TMP, 'rb').read()).hexdigest()
    if  download_md5 != PHORONIX_MD5:
        LOG.exception("Remote phoronix debian package md5 mismatch (%s != %s)", download_md5, PHORONIX_MD5)

    # install phoronix
    cmd = PATH_SUDO + ' ' + PATH_DPKG + ' -i ' + PHORONIX_TMP
    LOG.debug("CMD: %s" % cmd)
    subprocess.check_call(cmd, shell=True)

    # setup phoronix so we're not prompted
    cmd = """echo -e 'y\ny\ny\ny\ny\ny\ny\ny\n' | """ + PATH_PHORONIX + ' batch-setup'
    LOG.debug("CMD: %s" % cmd)
    subprocess.check_call(cmd, shell=True)

def run_tests(args):
    """
    Main method to run all tests and output results

    """

    results = {}

    LOG.info("Beginning CloudBench tests")
    
    results.update(_run_tests_phoronix(args))
    results.update(_run_tests_iobench(args))
    
    LOG.info("All CloudBench tests completed")
    
    # debug output of results
    LOG.debug("Test Result Dump: %r" % results)
    
    # parse the results for the tests we expect
    with open(PATH_RESULT_CSV, 'w') as f:
        hostname = __get_hostname()
        f.write('hostname,test_name,test_description,test_result\n')
        for k in results.keys():
            f.write('%s,%s,%s,%s\n' % (hostname, k, results[k]['name'], results[k]['result']))
            
def __get_hostname():
    """
    Return the system hostname
    """
    return socket.gethostname()

def __get_io_test_size(args):
    """
    Return the IOBench Test Size based on command line args
    """
    cmd = "free -m | grep Mem: | awk '{print $2}'"
    LOG.debug("CMD: %s", cmd)
    ram = int(subprocess.check_output(cmd, shell=True).strip())
    if args.iobench_type == 'short':
        size_m = args.iobench_short_size
        size_k = size_m*1024
    elif args.iobench_type == 'long':
        size_m = ram*2
        size_k = size_m*1024        
    else:
        LOG.exception("Invalid iobench type %s specified, valid values are short or long", args.iobench_type)
        raise CloudBenchException
    return (size_m, size_k)

def __run_phoronix_test(name, test, regexp):
    """
    Helper method to run a phoronix test and parse the results
    """

    LOG.info("Installing phoronix test %s", name)
    cmd = 'phoronix-test-suite install ' + test
    LOG.debug("CMD: %s", cmd)
    subprocess.check_call(cmd, shell=True)

    # parse individual tests
    LOG.info("Running phoronix test %s", name)
    cmd = PATH_PHORONIX + ' batch-run ' + test
    LOG.debug("CMD: %s" % cmd)
    output = subprocess.check_output(cmd, shell=True)
    result = re.search(regexp, output)
    if not result:
        LOG.exception("The phoronix test %s produced unknown output: %s" % (test, output))
        raise CloudBenchException
    return {
        test: {
                 'name': name,
                 'result': result.groups()[0]
        }
    }

def __run_iobench_test(size_m, size_k):
    """
    Helper method to run all iobench tests and parse the results
    """

    results = {}

    # iozone
    LOG.info("Running 16k record size IOZone Direct I/O bandwidth test")
    cmd = "cd %s && iozone -I -A -g %sm -n %sm -r 16 | grep %s | grep -v maximum | grep -v minimum" % (IOBENCH_PATH, size_m, size_m, size_k)
    LOG.debug("CMD: %s", cmd)
    output = subprocess.check_output(cmd, shell=True)
    cols = re.split('\s+', output.strip())
    results.update({
         'iozone': {
             'name': 'IOZone I/O Throughput Test',
             'result': "Write %s MB/s Read %s MB/s" % (int(cols[2])/1024, int(cols[4])/1024)
         }
     })
    
    LOG.info("Write %s MB/s Read %s MB/s" % (int(cols[2])/1024, int(cols[4])/1024))

    # fio    
    for (test_name, fio_hdr, fio_rw, fio_blocksize, fio_ioengine, regexp) in REQUIRED_FIO_TESTS:
        
        fio_test_file = os.path.join('/tmp', '%s.fio' % fio_hdr)
        fio_test_out = os.path.join('/tmp', '%s.output' % fio_hdr)
        
        with open(fio_test_file, 'w') as f:
            f.write('; %s %smb of data\n' % (test_name, str(size_m)))
            f.write('[%s]\n' % fio_hdr)
            f.write('direct=1\n')
            f.write('buffered=0\n')
            f.write('rw=%s\n' % fio_rw)
            f.write('size=%sm\n' % size_m)
            f.write('blocksize=%s\n' % fio_blocksize)
            f.write('directory=%s\n' % IOBENCH_PATH )
            
            if fio_ioengine:
                f.write('ioengine=%s\n' % fio_ioengine)
    
        LOG.info("Running test %s" % test_name)
        cmd = "fio --output=%s %s" % (fio_test_out, fio_test_file)
        LOG.debug("CMD: %s" % cmd)
        subprocess.check_call(cmd, shell=True)
        output = open(fio_test_out, 'r').read()
        result = re.search(regexp, output)
        if not result:
             LOG.exception("The fio test %s produced unknown output: %s", test_name, output)
             raise CloudBenchException
        results.update({
            fio_hdr: {
                'name': test_name,
                'result': "%s IOPS" % result.groups()[0]
            }
        })
        LOG.info("Test results for %s: %s IOPS", test_name, result.groups()[0])

    LOG.info("Running IOPing write latency tests")
    cmd = "ioping -B -D -c 3 %s" % IOBENCH_PATH
    output = subprocess.check_output(cmd, shell=True)
    ping_results = output.split()
    if not result:
        LOG.exception("The ioping test produced unknown output: %s", output)
        raise CloudBenchException
    LOG.info("IOPing write latency %susec", ping_results[5])
    results.update({
        'ioping': {
            'name': 'IOPing Write Latency Test',
            'result': "%susec" % ping_results[5]
        }
    })
    return results

def _run_tests_phoronix(args):
    """
    Run phoronix tests
    """

    phoronix_results = {}

    with open(expanduser("~") + '/.phoronix-test-suite/user-config.xml', 'w') as f:
        f.write('''<?xml version="1.0"?>
            <!--Phoronix Test Suite v3.8.0 (Bygland)-->
            <?xml-stylesheet type="text/xsl" href="xsl/pts-user-config-viewer.xsl"?>
            <PhoronixTestSuite>
              <Options>
                <OpenBenchmarking>
                  <AnonymousUsageReporting>FALSE</AnonymousUsageReporting>
                  <AnonymousSoftwareReporting>FALSE</AnonymousSoftwareReporting>
                  <AnonymousHardwareReporting>FALSE</AnonymousHardwareReporting>
                  <IndexCacheTTL>3</IndexCacheTTL>
                  <AlwaysUploadSystemLogs>FALSE</AlwaysUploadSystemLogs>
                </OpenBenchmarking>
                <General>
                  <DefaultBrowser></DefaultBrowser>
                  <UsePhodeviCache>TRUE</UsePhodeviCache>
                  <DefaultDisplayMode>DEFAULT</DefaultDisplayMode>
                </General>
                <Modules>
                  <LoadModules>toggle_screensaver, update_checker, graphics_event_checker</LoadModules>
                </Modules>
                <Installation>
                  <RemoveDownloadFiles>FALSE</RemoveDownloadFiles>
                  <SearchMediaForCache>TRUE</SearchMediaForCache>
                  <SymLinkFilesFromCache>FALSE</SymLinkFilesFromCache>
                  <PromptForDownloadMirror>FALSE</PromptForDownloadMirror>
                  <EnvironmentDirectory>~/.phoronix-test-suite/installed-tests/</EnvironmentDirectory>
                  <CacheDirectory>~/.phoronix-test-suite/download-cache/</CacheDirectory>
                </Installation>
                <Testing>
                  <SaveSystemLogs>TRUE</SaveSystemLogs>
                  <SaveInstallationLogs>FALSE</SaveInstallationLogs>
                  <SaveTestLogs>FALSE</SaveTestLogs>
                  <RemoveTestInstallOnCompletion></RemoveTestInstallOnCompletion>
                  <ResultsDirectory>~/.phoronix-test-suite/test-results/</ResultsDirectory>
                  <AlwaysUploadResultsToOpenBenchmarking>FALSE</AlwaysUploadResultsToOpenBenchmarking>
                </Testing>
                <TestResultValidation>
                  <DynamicRunCount>TRUE</DynamicRunCount>
                  <LimitDynamicToTestLength>20</LimitDynamicToTestLength>
                  <StandardDeviationThreshold>3.50</StandardDeviationThreshold>
                  <ExportResultsTo></ExportResultsTo>
                </TestResultValidation>
                <BatchMode>
                  <SaveResults>TRUE</SaveResults>
                  <OpenBrowser>FALSE</OpenBrowser>
                  <UploadResults>FALSE</UploadResults>
                  <PromptForTestIdentifier>FALSE</PromptForTestIdentifier>
                  <PromptForTestDescription>FALSE</PromptForTestDescription>
                  <PromptSaveName>FALSE</PromptSaveName>
                  <RunAllTestCombinations>TRUE</RunAllTestCombinations>
                  <Configured>TRUE</Configured>
                </BatchMode>
                <Networking>
                  <NoNetworkCommunication>FALSE</NoNetworkCommunication>
                  <Timeout>20</Timeout>
                  <ProxyAddress></ProxyAddress>
                  <ProxyPort></ProxyPort>
                </Networking>
              </Options>
            </PhoronixTestSuite>
        ''')

    # install all tests
    for name, test, regexp in REQUIRED_PHORONIX_TESTS:
        phoronix_results.update(__run_phoronix_test(name, test, regexp))

    return phoronix_results

def _run_tests_iobench(args):
    """
    Run phoronix tests
    """

    size_m, size_k = __get_io_test_size(args)
    results = __run_iobench_test(size_m, size_k)
    return results
    

if __name__ == '__main__':

    args = parse_args()
    setup_logging(args)

    try:
        run(args)
        sys.exit(0)
    except Exception as err:
        LOG.exception(err)
        sys.exit(1)
    except CloudBenchException:
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(1)
