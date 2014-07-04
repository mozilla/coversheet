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

def download(url, destination=None):
    # Ensure we have a properly encoded URL
    url = urllib.quote(url, safe='%/:=&?~#+!$,;\'@()*[]')

    if destination:
        if not os.path.exists(destination):
            os.makedirs(destination)
        file_name = os.path.join(destination, url.split('/')[-1])
    else:
        file_name = url.split('/')[-1]

    request = urllib2.urlopen(url)
    with open(file_name, 'wb') as file:
        print "Downloading: %s" % (file_name)
        for chunk in iter(lambda: request.read(CHUNK_SIZE), ''):
            file.write(chunk)

    return os.path.abspath(file_name)

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

    # This will be changed in issues 30
    # https://github.com/mozilla/coversheet/issues/30
    password = 'crossweaveservicescrossweaveservices'
    username = 'crossweaveservices@restmail.net'

    # Download the build and tests package
    build = download(url=options.urlbuild, destination='builds')
    packaged_tests = download(url=options.urltest)

    # Unzip the packaged tests
    with zipfile.ZipFile(packaged_tests) as zip:
        zip.extractall('tests')

    # Create the virtual environment
    current_location = os.getcwd()
    create_venv_script = os.path.abspath(os.path.join('tests', 'tps',
                                                      'create_venv.py'))
    tps_env = os.path.abspath('tps-env')

    # Bug 1030768, setup.py has to be called from it's own location
    os.chdir(os.path.abspath(os.path.join('tests', 'tps')))
    subprocess.check_call(['python', create_venv_script,
                           '--username', username,
                           '--password', password,
                           tps_env])
    os.chdir(current_location)


    if sys.platform == 'win32':
        env_activate_file = os.path.join(tps_env, 'Scripts', 'activate_this.py')
    else:
        env_activate_file = os.path.join(tps_env, 'bin', 'activate_this.py')

    # Activate the environment from file and set the VIRTUAL_ENV os variable
    execfile(env_activate_file, dict(__file__=env_activate_file))
    os.environ['VIRTUAL_ENV'] = tps_env

    # After activating the environment we import the mozinstall module
    import mozinstall

    build_path = mozinstall.install(build, os.path.join(os.getcwd(), 'binary'))

    # Get the path to the binary and prepare the process arguments
    binary = mozinstall.get_binary(build_path, 'firefox')
    tps_cmd_args = ['runtps', '--binary', binary]

    if debug:
        tps_cmd_args.append('--debug')

    # Call the tps testrun, if it throws, exit the process
    # and flag the build as failed
    try:
        subprocess.check_call(tps_cmd_args)
    except subprocess.CalledProcessError as e:
        sys.exit(e)

if __name__ == "__main__":
    main()
