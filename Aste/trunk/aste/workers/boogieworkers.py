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

from aste.workers.workers import BuildWorker
from aste.workers.mixins import TestRunnerMixin
from aste.utils.misc import zip_directory

class BoogieWorker(TestRunnerMixin, BuildWorker):
    """Implements the steps necessary to build Boogie.
    """
    
    def __init__(self, env):
        super(BoogieWorker, self).__init__(env, 'Boogie')
        
    def copySpecSharpToBoogie(self):
        self.cd(self.cfg.Paths.Boogie + "\Binaries")
        cmd = "%s SPECSHARPROOT=%s" % (self.cfg.Apps.nmake, self.cfg.Paths.SpecSharp)
        self.runSafely(cmd)

    def buildBoogie(self):
        self.cd(self.cfg.Paths.Boogie + "\Source")
        cmd = "%s Boogie.sln /Build Debug" % self.cfg.Apps.devenv
        self._runDefaultBuildStep(cmd)

    def buildDafny(self):
        self.cd(self.cfg.Paths.Boogie + "\Source")
        cmd = "%s Dafny.sln /Build Debug" % self.cfg.Apps.devenv
        self._runDefaultBuildStep(cmd)

    def testBoogie(self):
        failed = self.runTestFromAlltestsFile(
            self.cfg.Paths.Boogie + "\\Test\\alltests.txt", 'testBoogie',
            self.cfg.Flags.ShortTestsOnly)
            
        self.project_data['tests']['failed'] = failed

    def zip_binaries(self, filename):
        self.cd(self.cfg.Paths.Boogie + "\Binaries")
        cmd = "%s zip SPECSHARPROOT=%s" % (self.cfg.Apps.nmake, self.cfg.Paths.SpecSharp)
        self.runSafely(cmd)
        zip_directory("export", filename)

