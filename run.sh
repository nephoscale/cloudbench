#!/bin/bash -x

curl --location-trusted https://github.com/nephoscale/cloudbench/tarball/master -o /tmp/cloudbench.tgz
mkdir -p /tmp/cloudbench
tar --strip-components=1 -x -v -z -f /tmp/cloudbench.tgz -C /tmp/cloudbench
cd /tmp/cloudbench
nohup ./bench.py --deps > /tmp/cloudbench.log
tail -f /tmp/cloudbench.log
