#!/bin/sh

curl --location-trusted https://github.com/nephoscale/cloudbench/tarball/master -o /tmp/cloudbench.tgz
cd /tmp
tar xvfz cloudbench.tgz
nohup ./bench.py --deps
