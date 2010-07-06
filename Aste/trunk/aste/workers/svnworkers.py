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
from aste.utils.misc import ensure_directories_exist

"""
 .. todo::
        Make it optional to not include the SVN checkout output (list of files)
        in the logs.

.. todo::
        Replace code pattern::

            ...
            result = self.run(...)
            ...
            if result['returncode'] != 0
            ...
                    
        by runObserved(...).
"""
import re
import shutil
import os
from difflib import unified_diff
from aste.workers.workers import BaseWorker
from aste.aste import AsteException
from aste.workers.mixins import SVNMixin
import aste.utils.errorhandling as errorhandling

class CheckoutWorker(SVNMixin, BaseWorker):
    """Checks out the sources of Spec#, Boogie and SscBoogie. The build data is
    stored using the corresponding method name, e.g. ``getSpecSharp``, as the
    key.
    
    If the configuration variable ``SVN.Update`` is false then a fresh checkout
    is done each time the worker runs. If ``SVN.Update`` is true then the local
    copy is updated (if existing and checked out otherwise).
    """
    
    DID = 'CheckoutWorker'
    
    def __init__(self, env):
        super(CheckoutWorker, self).__init__(env)
        self.env.data[self.DID] = {}
    
    def _getSvnSource(self, svnUrl, destDir):
        """Checks out to or updates the local copy at ``destDir`` from the
        the SVN repository at ``svnUrl``, depending on the configuration
        variable ``SVN.Update``.
        
        Returns a dictionary with the ``returncode`` and the ``output`` of SVN, and
        the summary_current ``revision`` number.
        
        If the SVN command terminates with a non-zero return :func:`abort` is
        invoked to abort the execution.
        """
        if not self.cfg.SVN.Update:
            if os.path.exists(destDir):                
#                shutil.rmtree(destDir)     # Fails on Windows if a file inside
                                            # destDir is read-only.
                cmd = "rmdir /s/q %s" % destDir
                self.run(cmd, shell=True)

        if not os.path.exists(destDir):
            result = self.svn_checkout(svnUrl, destDir, auth=False)
        else:
            result = self.svn_update(destDir, auth=False)
            
        revisions = self.svn_get_revision_numbers(destDir)
        result.update(revisions)
        
        return result

    @errorhandling.add_context("Checking out Spec# from CodePlex")
    def getSpecSharp(self):
        """Downloads the Spec# sources from ``SVN.SpecSharp`` to
        ``Paths.SpecSharp``.
        """
        result = self._getSvnSource(self.cfg.SVN.SpecSharp, self.cfg.Paths.SpecSharp)
        self.env.data[self.DID]['getSpecSharp'] = result
        self.noteSummary('SpecSharp revision: %s' % result['last_changed_revision'],
                         prefix='# ')

    @errorhandling.exc_handler(AsteException, errorhandling.add_context,
                               context="Checking out Boogie from CodePlex")
    def getBoogie(self):
        """Downloads the Boogie sources from ``SVN.Boogie`` to
        ``Paths.Boogie``.
        """
        result = self._getSvnSource(self.cfg.SVN.Boogie, self.cfg.Paths.Boogie)
        self.env.data[self.DID]['getBoogie'] = result
        self.noteSummary('Boogie revision: %s' % result['last_changed_revision'],
                         prefix='# ')
        
    @errorhandling.exc_handler(AsteException, errorhandling.add_context,
                               context="Checking out SscBoogie from CodePlex")
    def getSscBoogie(self):
        """Downloads the SscBoogie sources from ``SVN.SscBoogie`` to
        ``Paths.SscBoogie``.
        """
        result = self._getSvnSource(self.cfg.SVN.SscBoogie, self.cfg.Paths.SscBoogie)
        self.env.data[self.DID]['getSscBoogie'] = result
        self.noteSummary('SscBoogie revision: %s' % result['last_changed_revision'],
                         prefix='# ')


class CommitSummaryWorker(SVNMixin, BaseWorker):
    """
    ..todo:: Couple with the date format used by the logger.
    """
    ignorePattern = re.compile('''
            \[\d{4}-\d{2}-\d{2}\ \d{2}:\d{2}:\d{2}\]
                |
            ^\#.*
        ''', re.VERBOSE) #  | re.MULTILINE
        
    summary_current = ''
    summary_checkout_dir = ''
    summary_checkout_file = ''
    summary_repo_dir = ''
    summary_repo_file = ''
    project = ''
    msg_prefix = ''
    
    def __init__(self, env, project):
        """
        ``project`` must be a key of the configuration entry 'CommitSummary'.
        If requested, the current summary file will be copied to and committed
        from the directory 'CommitSummary.project.From'.
        """

        super(CommitSummaryWorker, self).__init__(env)
        
        self.project = project
        
        self.summary_current = self.cfg.Logging.SummaryLog
        
        self.summary_repo_dir = self.cfg.CommitSummary[project].To
        self.summary_repo_file = "%s/%s" % (
            self.cfg.CommitSummary[project].To,
            os.path.basename(self.summary_current))
          
        self.summary_checkout_dir = self.cfg.CommitSummary[project].From
        self.summary_checkout_file = os.path.join(
            self.summary_checkout_dir, os.path.basename(self.summary_current))
    
    def commit_summary_if_changed(self, msg_prefix=''):
        self.msg_prefix = msg_prefix
        committed = False

        if self.hasStatusChanged():
            if self.cfg.Flags.UploadSummary:
                self.commitCurrentSummary()
                committed = True
            else:
                self.note(("Summary (project=%s) has changed but won't be " +
                           "committed due to configuration flag " +
                           "'Flags.UploadSummary'.") % self.project)
        else:
            self.note(("Summary (project=%s) hasn't changed and won't be " +
                       "committed.") % self.project)
            
        return committed

    

    def hasStatusChanged(self):
        # Remove the local folder that contains the checkout of the repo
        # summary, if existing.
        if os.path.exists(self.summary_checkout_dir):
            cmd = "rmdir /s/q %s" % self.summary_checkout_dir
            self.run(cmd, shell=True)

        # (Re)Create that folder.
        ensure_directories_exist(self.summary_checkout_dir)


        # Checkout the repo summary.
        self.svn_checkout(self.summary_repo_dir, self.summary_checkout_dir,
                          user=self.cfg.CommitSummary[self.project].User,
                          password=self.cfg.CommitSummary[self.project].Password)
        
        differs = True

        # Diff current against repo summary, if the latter exists.
        if os.path.isfile(self.summary_checkout_file):
            differs = len(self.diff(self.summary_current,
                                    self.summary_checkout_file)) != 0

        return differs
            
    def diff(self, summaryA, summaryB):
        summaryA = self._readAndPrepare(summaryA)
        summaryB = self._readAndPrepare(summaryB)
        
        # Returns a generator producing the actual differences.
        # Attention: since diff is a generator it will only return its
        # content, i.e. the textual delta, only once!
        diff = unified_diff(summaryA, summaryB)
        diffstr = "".join(diff)

        return diffstr
        
    def _readAndPrepare(self, summary):
        with open(summary) as fh:
            lines = []

            for line in fh:
                lines.append(self.ignorePattern.sub('', line))

        return lines
    
    def commitCurrentSummary(self):
        self.commitSummary(self.summary_current)
    
    def commitSummary(self, summary):
        self._commitSummary(summary)
    
    def _commitSummary(self, summary):
        """
        .. todo:: Make message configurable via config file.
        """

        shutil.copyfile(summary, self.summary_checkout_file)

        # Ensure that the summary we are about to commit has already been
        # added to the repo.
        self.svn_ensure_version_controlled(
            self.summary_checkout_file,
            user=self.cfg.CommitSummary[self.project].User,
            password=self.cfg.CommitSummary[self.project].Password)
        
        # Commit the current summary.
        msg = "[Aste] %sCommitting summary due to changes." % self.msg_prefix
        self.svn_commit(self.summary_checkout_file, msg,
                        user=self.cfg.CommitSummary[self.project].User,
                        password=self.cfg.CommitSummary[self.project].Password)