# This script will be replaced by issue #17
# https://github.com/mozilla/coversheet/issues/17
# For job testing purpose I will add just the options so it won't throw

import optparse

def main():
    parser = optparse.OptionParser()
    parser.add_option('--urltest',
                      action='store',
                      type='string',
                      dest='urltest',
                      default=None,
                      help='The URL to the Firefox tests on the FTP server')
    parser.add_option('--urlbuild',
                      action='store',
                      type='string',
                      dest='urlbuild',
                      default=None,
                      help='The URL to the Firefox build on the FTP server')
    parser.add_option('--debug',
                      action='store',
                      dest='debug',
                      default='false',
                      help='run in debug mode')
    parser.add_option('--mobile',
                      action='store_true',
                      dest='mobile',
                      default=False,
                      help='run with mobile settings')
    (options, args) = parser.parse_args()

    print options

if __name__ == "__main__":
    main()