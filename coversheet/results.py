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
import socket
import traceback


class Covresults(object):
  """Class for handling coversheet test-run results."""

  def __init__(self, config, autolog, emailresults, filename):
    self.config = config
    self.filename = filename
    self.autolog = autolog
    self.emailresults = emailresults

  def readResults(self):
    """Reads in the results from the tps test run json file."""
    f = open(self.filename, 'r')
    fileContents = f.read()
    f.close()
    self.test = json.loads(fileContents)

  def handleResults(self):
    """Handles sending of results to the appropriate destinations."""
    self.readResults()
    self.postdata = self.test['results']
    if self.postdata.has_key('numpassed'):
      self.numpassed = self.postdata['numpassed']
    if self.postdata.has_key('numfailed'):
      self.numfailed = self.postdata['numfailed']
    self.firefoxrunnerurl = self.postdata.get('firefoxrunnerurl', 'unknown')
    self.synctype = self.postdata.get('synctype', '')

    if self.postdata.has_key('body'):
      body = self.postdata['body']
    else:
      body = None
    sendTo = self.postdata['sendTo']

    if self.autolog:
      self.postToAutolog()

    if self.emailresults:
      try:
        self.sendEmail(body, sendTo)
      except:
        traceback.print_exc()

  def sendEmail(self, body=None, sendTo=None):
    """Send the result email"""
    if self.config.get('email') and self.config['email'].get('username')  \
       and self.config['email'].get('password'):
      from sendemail import SendEmail
      from emailtemplate import GenerateEmailBody

      if body is None:
        buildUrl = None
        if self.firefoxrunnerurl:
          buildUrl = self.firefoxrunnerurl
        body = GenerateEmailBody(self.postdata,
                                 self.numpassed,
                                 self.numfailed,
                                 self.config['account']['serverURL'],
                                 buildUrl)

      subj = "TPS Report: "
      if self.numfailed == 0 and self.numpassed > 0:
        subj += "YEEEAAAHHH"
      else:
        subj += "PC LOAD LETTER"

      changeset = self.postdata['productversion']['changeset'] if \
          self.postdata and self.postdata.get('productversion') and \
          self.postdata['productversion'].get('changeset') \
          else 'unknown'
      subj +=", changeset " + changeset + "; " + str(self.numfailed) + \
             " failed, " + str(self.numpassed) + " passed"

      To = [sendTo] if sendTo else None
      if not To:
        if self.numfailed > 0 or self.numpassed == 0:
          To = self.config['email'].get('notificationlist')
        else:
          To = self.config['email'].get('passednotificationlist')

      if To:
        SendEmail(From=self.config['email']['username'],
                  To=To,
                  Subject=subj,
                  HtmlData=body,
                  Username=self.config['email']['username'],
                  Password=self.config['email']['password'])

  def postToAutolog(self):
    from mozautolog import RESTfulAutologTestGroup as AutologTestGroup

    group = AutologTestGroup(
              harness='crossweave',
              testgroup='crossweave-%s' % self.synctype,
              server=self.config.get('es'),
              restserver=self.config.get('restserver'),
              machine=socket.gethostname(),
              platform=self.config.get('platform', None),
              os=self.config.get('os', None),
            )
    tree = self.postdata['productversion']['repository']
    group.set_primary_product(
              tree=tree[tree.rfind("/")+1:],
              version=self.postdata['productversion']['version'],
              buildid=self.postdata['productversion']['buildid'],
              buildtype='opt',
              revision=self.postdata['productversion']['changeset'],
            )
    group.add_test_suite(
              passed=self.numpassed,
              failed=self.numfailed,
              todo=0,
            )
    for test in self.postdata['tests']:
      if test['state'] != "TEST-PASS":
        # XXX FIX ME
        #errorlog = self.errorlogs.get(test['name'])
        #errorlog_filename = errorlog.filename if errorlog else None
        errorlog_filename = None
        group.add_test_failure(
              test = test['name'],
              status = test['state'],
              text = test['message'],
              logfile = errorlog_filename
            )
    try:
        group.submit()
    except:
        self.sendEmail('<pre>%s</pre>' % traceback.format_exc(),
                       sendTo='crossweave@mozilla.com')
        return

    # Iterate through all testfailure objects, and update the postdata
    # dict with the testfailure logurl's, if any.
    for tf in group.testsuites[-1].testfailures:
      result = [x for x in self.postdata['tests'] if x.get('name') == tf.test]
      if not result:
        continue
      result[0]['logurl'] = tf.logurl
