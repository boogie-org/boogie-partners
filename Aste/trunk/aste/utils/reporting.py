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
Functionality related to creating reports.
"""

import os
import textwrap

def _concat(what, to):
    if not what.endswith('\n'):
        what += '\n'
        
    if to:
        to += "\n" + what
    else:
        to = what
        
    return to

class AsteExceptionFormatter(object):
    WIDTH = 80
    INDENT = '  '
    __main_wrapper = None
    __dict_wrapper = None
    __text = ""
    
    def __init__(self):
        self.__main_wrapper = textwrap.TextWrapper(
            width=self.WIDTH, initial_indent=self.INDENT,
            subsequent_indent=self.INDENT)
                                       
        self.__dict_wrapper = textwrap.TextWrapper(
            width=self.WIDTH - len(self.INDENT),
            initial_indent=self.INDENT, subsequent_indent=self.INDENT * 3)
    
    def format(self, exc):
        self.__text = ""
        
        self.__add_if_set("Error context", exc.context)
        self.__add_if_set("Error message", exc.message)
        self.__add_subdict_if_set(exc.message_values)
        
        if not self.__text.endswith("\n"):
            self.__text += "\n"

        return self.__text
        
    def __add_subdict_if_set(self, dictionary):
        pairs = ""

        if len(dictionary) > 0:
            pairs = ["%s=%s" % (k, v) for k,v in dictionary.items()]
            pairs = "\n".join([self.__dict_wrapper.fill(pair) for pair in pairs])

            self.__text += "\n\n" + pairs

    def __add_if_set(self, title, text):
        if text:
            textlines = text.split('\n')
            maxlen = max([len(line) for line in textlines])
            
            if maxlen > self.WIDTH:
                text = self.__main_wrapper.fill(text)
            else:
                text = "\n".join(["  " + line for line in textlines])
            
            self.__text = _concat("%s:\n%s" % (title, text), self.__text)


class BuildStatusReportGenerator(object):
    INDENT = AsteExceptionFormatter.INDENT
    __text = ""
    __env = None
    
    def __init__(self, env):
        self.__env = env
    
    def generate_report(self):
        self.__text = ""

        projects_data = self.__env.data['projects']

        for project in projects_data:
            data = projects_data[project]

            text = project + ":"
            text = self.__append_revision_if_set(text, project)
            text += "\n"
            
            if data['build']['success'] and not data['tests']['failed']:
                text += self.INDENT + "OK\n"
            else:                
                if not data['build']['success']:
                    text += self.INDENT + "Build failed\n"
                else:
                    # Tests must have failed
                    text += "%s%s %s\n" % (self.INDENT,
                        len(data['tests']['failed']), "test(s) failed")
                            
            if project in self.__env.data['commits']:
                text += self.INDENT + "Summary changed\n"
            
            self.__text = _concat(text, self.__text)
        
        return self.__text
    
    def generate_report_summary(self, exception=None):
        projects_data = self.__env.data['projects']
        
        summary = ''
        tests_failed = False
        summaries_comitted = len(self.__env.data['commits']) != 0 
        
        for project in projects_data:
            tests_failed = tests_failed or projects_data[project]['tests']['failed']

        pieces = []
        if exception: pieces.append(exception.__class__.__name__)
        if tests_failed: pieces.append('Tests failed')
        if summaries_comitted: pieces.append('Summaries committed')
        
        if pieces:        
            summary = ", ".join(pieces)
        else:
            summary = 'OK'
            
        return summary
    
    def assemble_additional_information(self):
        text = "Additional information:\n"
        text += self.INDENT + "Host id: %s\n" % self.__env.cfg.HostId
        text += self.INDENT + "Tests (only short): %s (%s)\n" % (
                            self.__env.cfg.Flags.Tests,
                            self.__env.cfg.Flags.ShortTestsOnly)
        text += self.INDENT + "Upload build: %s\n" % self.__env.cfg.Flags.UploadTheBuild 
        
        for project in self.__env.data['projects']:
            if (project in self.__env.cfg.CommitSummary
                and 'Url' in self.__env.cfg.CommitSummary[project]):
            
                text += self.INDENT + "%s summary: %s\n" % (
                    project, self.__env.cfg.CommitSummary[project].Url)
    
        return text
    
    def __append_revision_if_set(self, text, project):
        if 'CheckoutWorker' in self.__env.data:
            text += " r" + str(self.__env.data['CheckoutWorker']['get' + project]['last_changed_revision'])
            
        return text
