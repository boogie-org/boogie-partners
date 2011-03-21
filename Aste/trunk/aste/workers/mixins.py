# --------------------------------- LICENSE: ----------------------------------
# The file is part of Aste (pronounced "S-T"), an automatic build tool
# originally tailored towards Spec# and Boogie.
#
# Copyright (C) 2010  Malte Schwerhoff
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
# --------------------------------- :LICENSE ----------------------------------

"""
Contains classes that are intended to be used as mixins
(by inheriting from them) in the sense that they provide workers with
additional services.
Classes in this module should not be intended to be instantiated directly.

In order to avoid problems with multiple inheritance, the mixins should not
override existing methods.
"""

import os
import re
import time
from aste.workers import workers
import aste.utils.misc
from aste.aste import NonBuildError

class TestRunnerMixin(workers.BuildWorker):
    """
    A mixin for :class:`aste.workers.workers.BuildWorker` that adds the
    functionality to execute tests from an 'alltests.txt'-style file and record
    their runtimes.
    """

    def runTestFromAlltestsFile(self, filename, category, shortOnly=False):
        """
        Reads test cases from the 'alltests.txt'-style file ``filename``,
        executes them, records the runtimes in the build data under
        'timings/timings/<category>/<testcase>' where '<category>' is the given
        ``category`` and '<testcase>' is the name of the test case as taken from
        the alltests file. Finally, a summary of the results is logged.
        """

        path = os.path.dirname(filename)
        self.cd(path)

        # Matcher detecting a failed test case. The match group (*.?) captures
        # the name of the failing test case.
        matcher = [(
            ['(.*?) FAILED'], # non-greedy match
            [workers.accept], [str]
        )]

        # Number of executed tests
        tests = 0

        with open(filename, 'r') as fh:
            matches = []

            # Create a new global data entry for the timings in this category.
            # Existing timings (in memory, not on disc) in the category will be
            # overwritten.
            self.env.data['timings']['timings'][category] = {}
            timings = self.env.data['timings']['timings'][category]

            # Iterate over all tests in the given alltests-style file.
            for line in fh:
                row = re.split('\s+', line, 2)
                testcase = row[0]        # Name of the current test case
                testcat = row[1].lower() # Category of the current test (use, long, ...)

                # Decide whether or not to run the current test case.
                if testcat == 'use' or (testcat == 'long' and not shortOnly):
                    cmd = 'runtest.bat ' + testcase

                    # Execute the test and record the runtime.
                    startTime = time.time()
                    result = self.run(cmd)
                    elapsed = time.time() - startTime
                    elapsed = round(elapsed, 2)

                    # Store the elapsed runtime, search the output for failures and
                    # increase the number of executed test cases.
                    timings[testcase] = elapsed
                    matches += self.matchGroup(matcher, result['output'])
                    tests = tests + 1

        failed = len(matches)

        self.noteSummary("%s out of %s test(s) in %s failed"
                % (failed, tests, filename))

        if failed > 0:
            self.logSummary(str(matches))

        return matches


class SVNMixin(workers.BaseWorker):
    """
    A mixin for :class:`aste.workers.workers.BaseWorker` that adds the
    functionality to interact with SVN repositories.
    """

    __user = ""
    __password = ""

    def set_default_auth(self, user, password):
        """
        The ``password`` is expected to be rot47ed.
        """

        self.__user = user
        self.__password = password

    def _run_svn(self, arg, auth=True, user=None, password=None, abort=True):
        """
        .. todo:: Remove the abort-flag, we should play it safe and always
                  abort. If there are cases where a non-zero returncode
                  does not indicate an abort-worthy error, we should rather
                  pass an abort-detection function.
        """

        if user == None:
            user = self.__user

        if password == None:
            password = self.__password

        cmd = "%s %s --no-auth-cache --non-interactive" % (self.cfg.Apps.svn, arg)

        if auth:
            # logcmd does not contain the password, runcmd does.
            cmd += " --username %s --password %s" % (user, '%s')
            logcmd = cmd % '********'
            runcmd = cmd % aste.utils.misc.rot47(password)
        else:
            logcmd = cmd
            runcmd = cmd

        result = self.run(runcmd, logcmd=logcmd)

        if abort and result['returncode'] != 0:
            msg = "SVN action failed"
            self.abort(msg, command=logcmd, returncode=result['returncode'],
                       output=result['output'], exception_class=NonBuildError)

        return result

    def svn_ensure_version_controlled(self, path, auth=True, user=None,
                                      password=None, abort=True):
        """
        Ensures that ``path`` is under version control.
        **Note**: This will fail if more than the last part of ``path`` are
        not yet under version control!
        """

        result = self._run_svn('status ' + path, auth=auth, user=user,
                               password=password, abort=abort)

        if result['output'].startswith('?'):
            # SVN does not know about the path, hence we have to add it
            # to the repository.
            result = self._run_svn('add ' + path, auth=auth, user=user,
                                   password=password, abort=abort)

    def svn_update(self, path, auth=True, user=None, password=None, abort=True):
        arg = 'update %s' % path

        return self._run_svn(arg, auth=auth, user=user, password=password,
                             abort=abort)

    def svn_revert(self, path, abort=True):
        arg = 'revert ' + path

        return self._run_svn(arg, auth=False, abort=abort)

    def svn_get_revision_numbers(self, path, abort=True):
        """
        Returns the 'revision' and the 'last changed revision' number by
        matching the the output of ``svn info``.
        """

        result = self._run_svn('info ' + path, auth=False, abort=abort)

        revision = re.search('^Revision: (\d+)',
                             result['output'],
                             re.MULTILINE).group(1)
        revision = int(revision)

        last_changed_revision = re.search('^Last Changed Rev: (\d+)',
                                          result['output'],
                                          re.MULTILINE).group(1)
        last_changed_revision = int(last_changed_revision)

        return {
            'revision': revision,
            'last_changed_revision': last_changed_revision
        }

    def svn_checkout(self, url, localdir, auth=True, user=None, password=None,
                     abort=True):

        arg = 'checkout %s %s' % (url, localdir)

        return self._run_svn(arg, auth=auth, user=user, password=password,
                             abort=abort)

    def svn_commit(self, path, msg, auth=True, user=None, password=None,
                   abort=True):
        """
        Commits the ``path``, which must already be under version control.
        The ``password`` is expected to be rot47ed.
        """

        arg = 'commit -m "%s" %s' % (msg, path)

        return self._run_svn(arg, auth=auth, user=user, password=password,
                             abort=abort)
