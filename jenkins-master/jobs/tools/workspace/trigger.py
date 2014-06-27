# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from datetime import datetime
import optparse
import os
import subprocess
import sys
import urllib
import urllib2
import zipfile

CHUNK_SIZE = 8192


class RunTPS():
    def __init__(self, build_url, tests_url, debug=False):
        self.build_url = build_url
        self.debug = debug
        self.tests_url = tests_url

        # We declare the credentials here and we create the account
        # after we install the fxa-python-client
        self.username = 'coversheet-%s@restmail.net' % \
                        os.urandom(6).encode('hex')
        self.password = os.urandom(2).encode('hex')

    def cleanup(self):
        exception = None
        try:
            # Remove the account
            subprocess.check_call(['fxa-client', '-e', self.username,
                                   '-p', self.password, 'destroy'])
        except Exception as e:
            print "Failed to remove the Firefox account %s, " \
                  "please remove it manually"  % self.username
            exception = e

        try:
            import mozinstall
            mozinstall.uninstall(self.build_path)
        except Exception as e:
            print "Failed to remove the Firefox build, " \
                  "please remove it manually"
            exception = e

        if exception:
            sys.exit(exception)

    def download(self, url):
        # Ensure we have a properly encoded URL
        url = urllib.quote(url, safe='%/:=&?~#+!$,;\'@()*[]')

        file_name = url.split('/')[-1]
        request = urllib2.urlopen(url)
        with open(file_name, 'wb') as file:
            print "Downloading: %s" % (file_name)
            for chunk in iter(lambda: request.read(CHUNK_SIZE), ''):
                file.write(chunk)

        return os.path.abspath(file_name)

    def run(self):
        # Create and verify the Firefox account
        subprocess.check_call(['fxa-client', '-e', self.username,
                               '-p', self.password, 'create'])
        subprocess.check_call(['fxa-client', '-e', self.username,
                               '-p', self.password, 'verify'])

        tps_cmd_args = ['runtps', '--binary', self.binary]
        if self.debug:
            tps_cmd_args.append('--debug')
        subprocess.check_call(tps_cmd_args)

    def setup_env(self):
        # Download the build and tests package
        self.build = self.download(url=self.build_url)
        self.packaged_tests = self.download(url=self.tests_url)

        # Unzip the packaged tests
        with zipfile.ZipFile(self.packaged_tests) as zip:
            zip.extractall('tests')

        # Create the virtual environment
        current_location = os.getcwd()
        create_venv_script = os.path.abspath(os.path.join('tests', 'tps',
                                                          'create_venv.py'))
        tps_env = os.path.abspath('tps-env')

        # Bug 1030768, setup.py has to be called from it's own location
        os.chdir(os.path.abspath(os.path.join('tests', 'tps')))

        subprocess.check_call(['python', create_venv_script,
                               '--username', self.username,
                               '--password', self.password, tps_env])
        os.chdir(current_location)

        dir = 'Scripts' if sys.platform == 'win32' else 'bin'
        env_activate_file = os.path.join(tps_env, dir, 'activate_this.py')

        # Activate the environment and set the VIRTUAL_ENV os variable
        execfile(env_activate_file, dict(__file__=env_activate_file))
        os.environ['VIRTUAL_ENV'] = tps_env

        # Install the fxa-python-client
        subprocess.check_call(['pip', 'install', 'fxa-python-client'])

        # After activating the environment we import the mozinstall module
        import mozinstall

        # Install Firefox and get the binary
        self.build_path = mozinstall.install(self.build,
                                             os.path.join(current_location,
                                                          'binary'))
        self.binary = mozinstall.get_binary(self.build_path, 'firefox')



def main():
    parser = optparse.OptionParser()
    parser.add_option('--debug',
                      action='store',
                      dest='debug',
                      default='false',
                      help='run in debug mode')
    parser.add_option('--urlbuild',
                      action='store',
                      type='string',
                      dest='urlbuild',
                      default=None,
                      help='The URL to the Firefox build on the FTP server')
    parser.add_option('--urltest',
                      action='store',
                      type='string',
                      dest='urltest',
                      default=None,
                      help='The URL to the Firefox tests on the FTP server')
    (options, args) = parser.parse_args()

    debug = True if (options.debug == 'true') else False

    run_tps = RunTPS(build_url=options.urlbuild, tests_url=options.urltest,
                     debug=debug)

    try:
        run_tps.setup_env()
        run_tps.run()
    except subprocess.CalledProcessError as e:
        sys.exit(e)
    finally:
        run_tps.cleanup()

if __name__ == '__main__':
    main()
