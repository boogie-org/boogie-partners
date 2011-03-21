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
Aste start script. Initialises the required Aste environment
(configuration, logger, etc.) and performs a given task.

.. todo::
        Make committing summary and other result-dependent operations
        depending on the task that was performed.
        That way one can perform certain tasks without e.g. committing a
        summary that simply differs from the previous one because the task
        it reflects is a different one.
"""


import sys
import os

# Add the directory where this script resides to the Python path so
# that we can access our modules.
thisPath = os.path.realpath(os.path.dirname(sys.argv[0]))
sys.path.append(thisPath)

import traceback
from aste.utils import reflection
from optparse import OptionParser
from aste.aste import Environment, AsteException, BuildError
from aste.workers.resultworkers import StatusMailer
from aste.utils.misc import rot47
from aste.tasks.tasks import RecordTimings
import aste.utils.reporting as reporting


# Return codes
RC_OK = 0
RC_WRONG_PARAMETER = 10
RC_ERROR = 100
RC_BUILD_ERROR = 500


# Command-line parameters
# =======================

usage = """usage: %prog [options] <action> [action-args] [task-kwargs]

Actions:
  start:\t\t\tExecutes the specified task (see --task)
  rot47 <str>:\t\tPrints <str> encoded as rot47
"""

parser = OptionParser(usage=usage)

parser.add_option("-c", "--config", dest="config", metavar="FILE",
                  default="main.cfg", help="Configuration file [default: %default]")

parser.add_option("-t", "--task", dest="task",
                  default="aste.tasks.tasks.FullBuild", help="Task to execute [default: %default]")

parser.add_option("--no-file-logging", dest="noFileLogging", action="store_true",
                  default=False, help="Log to stdout only [default: %default]")

options, args = parser.parse_args()

if len(args) == 0:
    parser.print_help()
    exit(RC_WRONG_PARAMETER)

if args[0].lower() == 'rot47':
    if len(args) != 2:
        parser.print_help()
        exit(RC_WRONG_PARAMETER)
    else:
        print rot47(args[1])
        exit(RC_OK)

if args[0].lower() != 'start':
    parser.print_help()
    exit(RC_WRONG_PARAMETER)


# Setting up the environment
# ==========================

env = Environment(options)
task = reflection.get_class(options.task)(env)

mailer = StatusMailer(env)

mail_status = ''
mail_subject = ''
mail_body = ''
exception = None


# Run the task
# ============

# Transform cli arguments into kwargs arguments that will be passed to
# task.run().
kwargs = {}
for arg in args:
    if arg.count('=') == 1:
        key, value = arg.split('=', 1)
        kwargs[key] = value

# REMEMBER: An AsteException should only be thrown after all relevant
# context information have been logged. Thus, we don't need to log the
# exception here, after catching it.

try:
    task.run(**kwargs)

    RecordTimings(env).run()
except AsteException as err:
    trace = ""

    # The BuildError stack trace currently doesn't contain any helpful
    # information, hence we skip it.
    if not isinstance(err, BuildError):
        # Get and format only the trace, the error message itself is formatted
        # by the AsteExceptionFormatter.
        trace = "".join(traceback.format_list(traceback.extract_tb(sys.exc_info()[2])))
        trace = "\nTraceback (most recent call last):\n" + trace

    mail_body = reporting.AsteExceptionFormatter().format(err) + trace
    exception = err
except Exception as err:
    # Exceptions other than AsteException are always assumed to be
    # unexpected, not build-related errors.
    #
    mail_body = traceback.format_exc()
    mailer.reportError(mail_body) # Log the exception.
    exception = err
finally:
    generator = reporting.BuildStatusReportGenerator(env)

    mail_body = (generator.generate_report()
                 + "\n" + "-" * 70 + "\n"
                 + "\n" + mail_body
                 + "\n" + generator.assemble_additional_information())

    mail_subject = generator.generate_report_summary(exception=exception)

    mailer.send(mail_subject, mail_body)
