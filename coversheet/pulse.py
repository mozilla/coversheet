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

import json
import logging
import os
import socket

from pulsebuildmonitor import PulseBuildMonitor
from subproc import TPSSubproc
from results import Covresults


class TPSPulseMonitor(PulseBuildMonitor):

    def __init__(self, platform='linux', config=None,
                 autolog=False, emailresults=False, testfile=None,
                 logfile=None, resultfile=None, mobile=False,
                 ignore_unused_engines=False, **kwargs):
        self.buildtype = ['opt']
        self.autolog = autolog
        self.emailresults = emailresults
        self.testfile = testfile
        self.logfile = logfile
        self.resultfile = resultfile
        self.mobile = mobile
        self.ignore_unused_engines = ignore_unused_engines
        self.config = config
        f = open(config, 'r')
        configcontent = f.read()
        f.close()
        configjson = json.loads(configcontent)
        self.tree = configjson.get('tree', ['services-central'])
        self.platform = [configjson.get('platform', 'linux')]
        self.label=('crossweave@mozilla.com|tps_build_monitor_' +
                    socket.gethostname())

        self.logger = logging.getLogger('tps_pulse')
        self.logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler('tps_pulse.log')
        self.logger.addHandler(handler)

        self.results = Covresults(configjson, self.autolog, self.emailresults,
                                  self.resultfile)

        PulseBuildMonitor.__init__(self,
                                   trees=self.tree,
                                   label=self.label,
                                   logger=self.logger,
                                   platforms=self.platform,
                                   buildtypes=self.buildtype,
                                   builds=True,
                                   **kwargs)

    def on_pulse_message(self, data):
        key = data['_meta']['routing_key']

    def on_build_complete(self, builddata):
        print "================================================================="
        print json.dumps(builddata)
        print "================================================================="

        # Don't run tests if some conditions aren't met
        if not builddata.get('testsurl') or builddata.get('locale') != 'en-US' \
            or builddata.get('status') != 0:
            return

        if os.access(self.resultfile, os.F_OK):
            os.remove(self.resultfile)

        mysub = TPSSubproc(builddata=builddata,
                           emailresults=self.emailresults,
                           autolog=self.autolog,
                           testfile=self.testfile,
                           logfile=self.logfile,
                           config=self.config,
                           mobile=self.mobile,
                           resultfile=self.resultfile,
                           ignore_unused_engines=self.ignore_unused_engines)

        mysub.get_buildAndTests()
        mysub.setup_tps()
        mysub.update_config()
        mysub.call_testrunners()
        self.results.handleResults()
