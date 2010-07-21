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
from shutil import make_archive
import os


class SscBoogieWorker(TestRunnerMixin, BuildWorker):
    """Implements the steps necessary to build SscBoogie.
    """

    def __init__(self, env):
        super(SscBoogieWorker, self).__init__(env, 'SscBoogie')

    def buildSscBoogie(self):
        self.cd(self.cfg.Paths.SscBoogie + "\Binaries")
        cmd = "%s BOOGIEROOT=%s" % (self.cfg.Apps.nmake, self.cfg.Paths.Boogie)
        self.runSafely(cmd)

        self.cd(self.cfg.Paths.SscBoogie + "\Source")
        cmd = "%s SscBoogie.sln /Build Debug" % self.cfg.Apps.devenv
        self._runDefaultBuildStep(cmd)

    def testSscBoogie(self):
        failed = self.runTestFromAlltestsFile(
            self.cfg.Paths.SscBoogie + "\\Test\\alltests.txt", 'testSscBoogie',
            self.cfg.Flags.ShortTestsOnly)

        self.project_data['tests']['failed'] = failed

    def registerSscBoogie(self):
        self.cd(self.cfg.Paths.SscBoogie + "\Binaries")
        cmd = "%s BOOGIEROOT=%s" % (self.cfg.Apps.nmake, self.cfg.Paths.Boogie)
        self.runSafely(cmd)

    def zip_binaries(self, filename):
        self.cd(self.cfg.Paths.SscBoogie + "\Binaries")
        cmd = "%s zip BOOGIEROOT=%s" % (self.cfg.Apps.nmake, self.cfg.Paths.Boogie)
        self.runSafely(cmd)
        # make_archive expects an archive name without a filename extension.
        archive_name = os.path.splitext(os.path.abspath(filename))[0]
        root_dir = os.path.abspath("export")
        make_archive(archive_name, 'zip', root_dir)
