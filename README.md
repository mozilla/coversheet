# coversheet
Coversheet is a CI system for TPS, which allows to run tests for each daily
build of Firefox across all platforms.

## Setup
Before you can start the system the following commands have to be performed:

```bash
git clone git://github.com/mozilla/coversheet.git
cd coversheet
./setup.sh
```

You will need to have the Python header files installed:

* Ubuntu: Install the package via: `apt-get install python-dev`
* OSX, Windows: Install the latest [Python 2.7](http://www.python.org/getit/)

## Startup
To start Jenkins simply run `./start.py` from the coversheet directory. You
can tell when Jenkins is running by looking out for "Jenkins is fully up and
running" in the console output. You will also be able to view the web dashboard
by pointing your browser at http://localhost:8080/

If this is the first time you've started Jenkins, or your workspaces have
recently been deleted, you will need to run an admin job to finish the setup.
Open http://localhost:8080/view/+admin/ and build the 'scripts' job.

## Jenkins URL
If you intend to connect to this Jenkins instance from another machine (for
example connecting additional nodes) you will need to update the `Jenkins URL`
to the IP or DNS name. This can be found in http://localhost:8080/configure
under the section headed "Jenkins Location".

## Adding new Nodes
To add Jenkins slaves to your master you have to create new nodes. You can use
one of the example nodes (Windows XP and Ubuntu) as a template. Once done the
nodes have to be connected to the master. Therefore Java has to be installed on
the node first.

### Windows:
Go to [www.java.com/download/](http://www.java.com/download/) and install the
latest version of Java JRE. Also make sure that the UAC is completely disabled,
and the screensaver and any energy settings have been turned off.

### Linux (Ubuntu):
Open the terminal or any other package manager and install the following
packages:

```bash
sudo add-apt-repository ppa:webupd8team/java
sudo apt-get update
sudo apt-get install oracle-java7-installer
```

Also make sure that the screensaver and any energy settings have been turned
off.

After Java has been installed open the appropriate node within Jenkins from the
nodes web browser like:

    http://IP:8080/computer/windows_xp_32_01/

Now click the `Launch` button and the node should automatically connect to the
master. It will be used once a job for this type of platform has been requested
by the Pulse consumer.

## Using the Jenkins master as executor
If you want that the master node also executes jobs you will have to update its
labels and add/modify the appropriate platforms, e.g. `master mac 10.7 64bit`
for Mac OS X 10.7.

## Testing changes
In order to check that patches will apply and no Jenkins configuration changes
are missing from your changes you can run the `run_tests.sh` script. This uses
[Selenium](http://code.google.com/p/selenium/) and
[PhantomJS](http://phantomjs.org/) to save the configuration for each job and
reports any unexpected changes. Note that you will need to
[download](http://phantomjs.org/download.html) PhantomJS and put it in your
path in order for these tests to run.

## Merging branches
The main development on the coversheet code happens on the master branch. In
not yet specified intervals we are merging changesets into the staging branch.
It is used for testing all the new features before those go live on production.
When running those merge tasks you will have to obey the following steps:

1. Select the appropriate target branch
2. Run 'git rebase master' for staging or 'git rebase staging' for production
3. Run 'git pull' for the remote branch you want to push to
4. Ensure the merged patches are on top of the branch
5. Ensure that the Jenkins patch can be applied by running 'patch --dry-run -p1
 <config/%BRANCH%/jenkins.patch'
6. Run 'git push' for the remote branch

For emergency fixes we are using cherry-pick to port individual fixes to the
staging and production branch:

1. Select the appropriate target branch
2. Run 'git cherry-pick %changeset%' to pick the specific changeset for the
current branch
3. Run 'git push' for the remote branch

Once the changes have been landed you will have to update the staging or
production machines. Run the following steps:

1. Run 'git reset --hard' to remove the locally applied patch
2. Pull the latest changes with 'git pull'
3. Apply the Jenkins patch with 'patch -p1 <config/%BRANCH%/jenkins.patch'
4. Restart Jenkins
