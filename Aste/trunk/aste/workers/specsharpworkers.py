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
from aste.workers.mixins import ProjectWorkerMixin

class SpecSharpWorker(BuildWorker, ProjectWorkerMixin):
    """
    Implements the steps necessary to build Spec#.
    """

    def __init__(self, env):
        super(SpecSharpWorker, self).__init__(env)
        self.project_setup('SpecSharp')

    def registerSpecSharpLKG(self):
        self.cd(self.cfg.Paths.SpecSharp + "\Microsoft.SpecSharp\LastKnownGood9")

        cmd = "Register.cmd Clean %s " % self.cfg.Apps.regasm
        self.runSafely(cmd)

        cmd = "Register.cmd RegisterLKG %s " % self.cfg.Apps.regasm
        self.runSafely(cmd)

    def buildSpecSharp(self):
        self.cd(self.cfg.Paths.SpecSharp)
        cmd = "%s SpecSharp.sln /Build DebugCommandLine" % self.cfg.Apps.devenv
        self._runDefaultBuildStep(cmd)
        
        self.project_build_success = True
        self.project_tests_success = True # Vacously true :-)

    def buildSpecSharpCheckinTests(self):
        self.cd(self.cfg.Paths.SpecSharp)

        cmd = "%s SpecSharp.sln /Project \"Checkin Tests\" /Build" \
                % self.cfg.Apps.devenv

        self._runDefaultBuildStep(cmd)

    def registerSpecSharpCompiler(self):
        self.cd(self.cfg.Paths.SpecSharp)
        cmd = "%s SpecSharp.sln /Build Debug" % self.cfg.Apps.devenv
        self._runDefaultBuildStep(cmd)