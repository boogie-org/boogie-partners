import re

with open("verbose -- some errors.log") as fhin:
    text = fhin.read()

#
# http://blogs.msdn.com/b/msbuild/archive/2006/11/03/msbuild-visual-studio-aware-error-messages-and-message-formats.aspx
#

pattern = r"""
^(
    (?:                    # Origin (optional)
        (?:
            ([A-Z]:\\.*?)\((.*?)\)    # Absolute path followed by (line,column)
                |
            (.*?)                     # Or simply anything
        )(?::\ )                # followed by ": "
    )?
    [^:]?                    # Subcategory (optional)
    (error|warning)\         # Category (required)
    (\w+)                  # Code (required)
    (:\ .*)?               # Text (optional)
)$
"""

matches = re.findall(pattern, text, re.VERBOSE | re.MULTILINE)

for m in matches:
    print m[0]