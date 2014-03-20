# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is TPS.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Jonathan Griffin <jgriffin@mozilla.com>
#   Sam Garrett      <samdgarrett@gmail.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

import os
import shutil
import sys
import zipfile
import re
import subprocess
import json
import requests

import mozinfo
import mozinstall

class TPSSubproc():
    def __init__(self, builddata=None, emailresults=False,
                 testfile=None, logfile=None, config=None, autolog=False,
                 mobile=False, ignore_unused_engines=False,
                 resultfile=None):
        assert(builddata)
        assert(config)

        self.url = builddata['buildurl']
        self.testurl = builddata['testsurl']
        self.emailresults = emailresults
        self.testfile = testfile
        self.logfile = logfile
        self.config = config
        self.autolog = autolog
        self.mobile = mobile
        self.resultfile = resultfile
        self.ignore_unused_engines = ignore_unused_engines

    def update_download_progress(self, percent):
        sys.stdout.write("===== Downloaded %d%% =====\r"%percent)
        sys.stdout.flush()
        if percent >= 100:
            sys.stdout.write("\n")

    def download_url(self, url, outputPath):
        print "Downloading %s...\r" % url
        with open(outputPath, 'wb') as handle:
            request = requests.get(url, stream=True)
            if request.status_code != 200:
                print "Error downloading file status_code=%s" % request.status_code

            bytes_so_far = 0.0
            block_size = 16 * 1024
            total_size = int(request.headers['content-length'])
        
            for block in request.iter_content(block_size):
                if not block:
                    continue
                bytes_so_far += block_size
                percent = (bytes_so_far / total_size) * 100
                self.update_download_progress(percent)
                handle.write(block)

    def prepare_build(self, installdir='downloadedbuild', appname='firefox'):
        self.installdir = os.path.abspath(installdir)
        buildName = os.path.basename(self.url)
        pathToBuild = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   buildName)

        # delete the build if it already exists
        if os.access(pathToBuild, os.F_OK):
          os.remove(pathToBuild)

        # download the build
        self.download_url(self.url, pathToBuild)

        # install the build
        print "installing %s" % pathToBuild
        shutil.rmtree(self.installdir, True)
        installed_at = mozinstall.install(pathToBuild, self.installdir)

        # remove the downloaded archive
        os.remove(pathToBuild)

        binary = mozinstall.get_binary(installed_at, appname)
        return os.path.abspath(binary)

    def download_tests(self, installdir='downloadedtests'):
        self.testinstalldir = os.path.abspath(installdir)
        testsName = os.path.basename(self.testurl)
        pathToTests = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   testsName)

        # delete tests if they already exist
        if os.access(pathToTests, os.F_OK):
          os.remove(pathToTests)

        # download the tests
        print "downloading tests from %s" % self.testurl
        self.download_url(self.testurl, pathToTests)

        print "extracting test files to %s" % pathToTests 
        tempZipFile = zipfile.ZipFile(pathToTests)
        tempZipFile.extractall(path=self.testinstalldir)

        print "finished downloading test files"

        return self.testinstalldir

    def get_buildAndTests(self):
        if self.url is not None and ('http://' in self.url or 'ftp://' in self.url):
            self.binary = self.prepare_build()
            self.tests = self.download_tests()
        else:
            self.binary = self.binary

    def setup_tps(self):
        # Setup the downloaded TPS
        self.tpswd = os.path.join(self.tests, "tps")
        self.tpsenv = os.path.join(self.testinstalldir, "tpsenv")
        if os.access(self.tpsenv, os.F_OK):
            shutil.rmtree(self.tpsenv)
        print "Installing tps in %s" % self.tpsenv
        self.run_process(["sh",
                          os.path.join(self.tpswd, "INSTALL.sh"),
                          self.tpsenv],
                          self.tpswd,
                          ignoreFailures=True)
        print "TPS setup complete"

    def update_config(self):
        f = open(self.config, 'r')
        tpsconfig = f.read()
        configjson = json.loads(tpsconfig)
        configjson['testdir'] = os.path.join(self.tpswd, "tests")
        configjson['extensiondir'] = os.path.join(self.tpswd, "extensions")
        # Update our coversheet config file
        updateFile = open(self.config, 'w')
        updateFile.write(json.dumps(configjson))
        updateFile.close()
        print 'wrote config file to', self.config

        # Update relative testfile paths to point to our downloaded tests.
        if self.testfile and not os.path.isabs(self.testfile):
            self.testfile = os.path.join(self.tpswd, "tests", self.testfile)
        print "testfile: ", self.testfile

    def call_testrunners(self):
        # getting our python location
        bin_dir = 'Scripts' if sys.platform.startswith('win') else 'bin'
        python_exe = 'python.exe' if sys.platform.startswith('win') else 'python'
        python_path = os.path.join(self.tpsenv, bin_dir, python_exe)

        tps_cli = os.path.join(self.tpswd, "tps", "cli.py")
        # standard call
        self.run_process([python_path, tps_cli,
                          "--binary", self.binary,
                          "--testfile", self.testfile,
                          "--resultfile", self.resultfile,
                          "--logfile", self.logfile,
                          "--configfile", self.config,
                          "--mobile" if self.mobile else '',
                          "--ignore_unused_engines" if self.ignore_unused_engines else ''],
                          self.tpswd)

        # mobile call
        self.run_process([python_path, tps_cli,
                          "--binary", self.binary,
                          "--testfile", self.testfile,
                          "--resultfile", self.resultfile,
                          "--logfile", self.logfile,
                          "--configfile", self.config,
                          "--mobile",
                          "--ignore_unused_engines" if self.ignore_unused_engines else ''],
                          self.tpswd)

        # ... and again via the staging server, if credentials are present
        f = open(self.config, 'r')
        configcontent = f.read()
        f.close()
        configjson = json.loads(configcontent)
        stageaccount = configjson.get('stageaccount')
        if stageaccount:
          username = stageaccount.get('username')
          password = stageaccount.get('password')
          passphrase = stageaccount.get('passphrase')
          if username and password and passphrase:
            stageconfig = configjson.copy()
            stageconfig['account'] = stageaccount.copy()
            self.run_process([python_path, tps_cli,
                              "--binary", self.binary,
                              "--testfile", self.testfile,
                              "--resultfile", self.resultfile,
                              "--logfile", self.logfile,
                              "--configfile", stageconfig,
                              "--ignore_unused_engines" if self.ignore_unused_engines else ''],
                              self.tpswd)

    def run_process(self, params, cwd=None, ignoreFailures=False):
        process = subprocess.Popen(params, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, cwd=cwd)
        stdout, stderr = process.communicate() #this blocks until the subprocess is finished
        print stdout, stderr
        retcode = process.returncode
        if not ignoreFailures:
            assert(retcode == 0)
        return retcode

