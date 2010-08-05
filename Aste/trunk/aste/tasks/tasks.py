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
.. todo:: Document this module.
"""

import aste.utils.misc
from aste.aste import BuildError
from aste.workers.svnworkers import CheckoutWorker, CommitSummaryWorker
from aste.workers.specsharpworkers import SpecSharpWorker
from aste.workers.boogieworkers import BoogieWorker
from aste.workers.sscboogieworkers import SscBoogieWorker
from aste.workers.resultworkers import TimingsRecorder, ReleaseUploader
from aste.workers.miscworkers import TimingsCSVExporter
import aste.utils.errorhandling as errorhandling

class Task(object):
    _env = None

    def __init__(self, env):
        self._env = env

    @property
    def env(self):
        return self._env

    @property
    def cfg(self):
        return self.env.cfg


class CheckoutTask(Task):
    def run(self):
        checkoutWorker = CheckoutWorker(self.env)

        checkoutWorker.getSpecSharp()
        checkoutWorker.getBoogie()

        if self.cfg.Flags.SscBoogie:
            checkoutWorker.getSscBoogie()

class AbstractBuildTask(Task):
    """Abstract class"""

    def __init__(self, env, buildWorker):
        super(AbstractBuildTask, self).__init__(env)
        self.worker = buildWorker

    def build(self):
        """Abstract method"""
        pass

    def run(self, **kwargs):
        try:
            self.build(**kwargs)
        except BuildError as exception:
#            message = '%s build ' % self.project

#            if exception:
#                message += 'failed'
#            else:
#                message += 'succeeded'

#            tests_failed = len(self.worker.project_data['tests']['failed'])
#            if tests_failed != 0:
#                message += ", %s test(s) failed" % tests_failed

#            committer = CommitSummaryWorker(self.env, self.project)
#            if committer.commit_summary_if_changed(message=message):
#                self.env.data['commits'].append(self.project)

            # Forward exception to the next layer (it should finally reach
            # run.py and trigger an error mail.
            raise
        finally:
            self.commit_summary_if_changed(self.worker.project_data['build']['success'])

    def commit_summary_if_changed(self, success):
        message = '%s build ' % self.project

        if success:
            message += 'succeeded'
        else:
            message += 'failed'

        tests_failed = len(self.worker.project_data['tests']['failed'])
        if tests_failed != 0:
            message += ", %s test(s) failed" % tests_failed

        committer = CommitSummaryWorker(self.env, self.project)
        if committer.commit_summary_if_changed(message=message):
            self.env.data['commits'].append(self.project)

    def upload_release(self, worker, revision=None):
        """
        .. todo::
            "Complex" methods should be implemented by workers, such that
            merely call a worker's methods depending on configuration or
            environment values.
        """

        filename = self.project.lower() + "-nightly.zip"
        username = self.cfg.Nightlies[self.project].User
        password = aste.utils.misc.rot47(self.cfg.Nightlies[self.project].Password)
        projectname = self.cfg.Nightlies[self.project].Project

        if revision == None:
            # CheckoutWorker key is only presented if this current run
            # includes checking-out the sources, which might not be the case.
            if "CheckoutWorker" in self.env.data:
                revision = self.env.data["CheckoutWorker"]['get' + self.project]['last_changed_revision']
            else:
                revision = 0

        # ATTENTION: worker must implement zip_binaries() as expected!
        worker.zip_binaries(filename)
        ReleaseUploader(self.env).upload_release(projectname, revision,
                                                 username, password, filename)

        worker.noteSummary('Released nightly of %s' % self.project, prefix='# ')

    @property
    def project(self):
        return self.worker.project

class SpecSharpTask(AbstractBuildTask):
    def __init__(self, env):
        super(SpecSharpTask, self).__init__(env, SpecSharpWorker(env))

    @errorhandling.add_context("Building Spec#")
    def build(self):
        self.worker.project_data['build']['started'] = True

        self.worker.registerSpecSharpLKG()
        self.worker.buildSpecSharp()

        if self.cfg.Flags.Tests and self.cfg.Flags.CheckinTests:
            self.worker.buildSpecSharpCheckinTests()

        self.worker.registerSpecSharpCompiler()

        self.worker.project_data['build']['success'] = True

class BoogieTask(AbstractBuildTask):
    def __init__(self, env):
        super(BoogieTask, self).__init__(env, BoogieWorker(env))

    def runBuild(self):
        """
        .. todo:: Move buildDafny() to a dedicated worker and task.
        """
        self.worker.copySpecSharpToBoogie()
        self.worker.set_version_number()
        self.worker.buildBoogie()

        if self.cfg.Flags.Dafny:
            self.worker.buildDafny()

    def runTests(self):
        self.worker.testBoogie()

    @errorhandling.add_context("Building Boogie")
    def build(self):
        self.worker.project_data['build']['started'] = True
        self.runBuild()
        self.worker.project_data['build']['success'] = True

        if self.cfg.Flags.Tests:
            self.runTests()

            if self.cfg.Flags.UploadTheBuild:
                self.upload_release(self.worker)


class SscBoogieTask(AbstractBuildTask):
    def __init__(self, env):
        super(SscBoogieTask, self).__init__(env, SscBoogieWorker(env))

    @errorhandling.add_context("Building SscBoogie")
    def build(self):
        self.worker.project_data['build']['started'] = True
        self.worker.buildSscBoogie()
        self.worker.registerSscBoogie()
        self.worker.project_data['build']['success'] = True

        if self.cfg.Flags.Tests:
            self.worker.testSscBoogie()

            if self.cfg.Flags.UploadTheBuild:
                self.upload_release(self.worker)

class FullBuild(Task):
    def run(self):
        CheckoutTask(self.env).run()
        SpecSharpTask(self.env).run()
        BoogieTask(self.env).run()

        if self.cfg.Flags.SscBoogie:
            SscBoogieTask(self.env).run()

class BuildOnly(FullBuild):
    def run(self):
        self.cfg.Flags.Tests = False
        super(BuildOnly, self).run()

class RecordTimings(Task):
    @errorhandling.add_context("Recording test timings")
    def run(self):
        if len(self.env.data['timings']['timings']) > 0:
            worker = TimingsRecorder(self.env)
            worker.add(self.env.data['timings'])


class ExportTimingsCSV(Task):
    @errorhandling.add_context("Exporting test timings to a CSV file")
    def run(self):
        worker = TimingsCSVExporter(self.env)
        worker.export(self.cfg.Timings.CSV)
