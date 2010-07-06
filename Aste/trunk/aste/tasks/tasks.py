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

class BuildTask(Task):
    """Abstract class"""

    # Must be set by the inheriting class!
    project = ''
    
    def build(self):
        """Abstract method"""
        pass
    
    def run(self, **kwargs):
        committer = CommitSummaryWorker(self.env, self.project)
        msg_prefix = 'Success: '
        
        try:
            self.build(**kwargs)
        except BuildError:
            # Forward exception to the next layer (it should finally reach
            # run.py and trigger an error mail.
            msg_prefix = 'Error: '
            raise
        finally:
            if committer.commit_summary_if_changed(msg_prefix=msg_prefix):
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
            revision = self.env.data["CheckoutWorker"]['get' + self.project]['last_changed_revision']
        
        # ATTENTION: worker must implement zip_binaries() as expected!
        worker.zip_binaries(filename)
        ReleaseUploader(self.env).upload_release(projectname, revision,
                                                 username, password, filename)
        
        worker.noteSummary('Released nightly of %s' % self.project, prefix='# ')

class SpecSharpTask(BuildTask):
    project = 'SpecSharp'
    
    @errorhandling.add_context("Building Spec#")
    def build(self):
        sscWorker = SpecSharpWorker(self.env)

        sscWorker.registerSpecSharpLKG()
        sscWorker.buildSpecSharp()

        if self.cfg.Flags.Tests and self.cfg.Flags.CheckinTests:
            sscWorker.buildSpecSharpCheckinTests()

        sscWorker.registerSpecSharpCompiler()

class BoogieTask(BuildTask):
    project = 'Boogie'    
    boogieWorker = None
    
    def __init__(self, env):
        super(BoogieTask, self).__init__(env)
        self.boogieWorker = BoogieWorker(self.env)
        
    def runBuild(self):
        """
        .. todo:: Move buildDafny() to a dedicated worker and task.
        """
        self.boogieWorker.copySpecSharpToBoogie()
        self.boogieWorker.buildBoogie()
        
        if self.cfg.Flags.Dafny:
            self.boogieWorker.buildDafny()
        
    def runTests(self):
        self.boogieWorker.testBoogie()
    
    @errorhandling.add_context("Building Boogie")    
    def build(self):
        self.runBuild()
        if self.cfg.Flags.Tests:
            self.runTests()

            if self.cfg.Flags.UploadTheBuild:
                self.upload_release(self.boogieWorker)


class SscBoogieTask(BuildTask):
    project = 'SscBoogie'
    
    @errorhandling.add_context("Building SscBoogie")
    def build(self): 
        sscBoogieWorker = SscBoogieWorker(self.env)
        sscBoogieWorker.buildSscBoogie()
        
        if self.cfg.Flags.Tests:
            sscBoogieWorker.testSscBoogie()

            if self.cfg.Flags.UploadTheBuild:
                self.upload_release(sscBoogieWorker)

        sscBoogieWorker.registerSscBoogie()
        
        
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