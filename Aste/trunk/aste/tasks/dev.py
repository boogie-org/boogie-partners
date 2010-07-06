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
Development tasks, not intended to be run from a productive system.
"""
from aste.tasks.tasks import Task, BuildTask
from aste.workers.specsharpworkers import SpecSharpWorker
from aste.workers.boogieworkers import BoogieWorker
from aste.workers.sscboogieworkers import SscBoogieWorker
from aste.workers.svnworkers import CommitSummaryWorker

class SpecSharpCheckinTests(Task):
    def run(self):
        sscWorker = SpecSharpWorker(self.env)
        sscWorker.buildSpecSharpCheckinTests()

class TestBoogie(Task):
    def run(self):
        boogieWorker = BoogieWorker(self.env)
        boogieWorker.testBoogie()
        
class TestSscBoogie(Task):
    def run(self):
        sscBoogieWorker = SscBoogieWorker(self.env)
        sscBoogieWorker.testSscBoogie()

class DiffLogs(Task):
    def run(self, **kwargs):
        worker = CommitSummaryWorker(self.env)
        diff = worker.diff(kwargs['file1'], kwargs['file2'])

        print diff
        
class Noop(Task):
    def run(self): pass
        # Does nothing
        
class ReleaseBothBoogies(BuildTask):
    def run(self):
        projects = [
            ('Boogie', BoogieWorker(self.env)),
            ('SscBoogie', SscBoogieWorker(self.env))
        ]
        
        for name, worker in projects:
            self.project = name
            self.upload_release(worker, revision_number=0)