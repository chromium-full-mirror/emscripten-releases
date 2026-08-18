#   Copyright 2026 WebAssembly Community Group participants
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os

import buildbot
import proc


def GitRevision(cwd=None):
    return proc.check_output(['git', 'rev-parse', 'HEAD'], cwd=cwd, text=True).strip()


def RevisionModifiesFile(f):
    """Return True if the file f is modified in HEAD commit.

    Exception: When running on trybots the current revision is not yet committed
    so we look for local changes in the working tree instead.
    """
    if not os.path.isfile(f):
        return False
    cwd = os.path.dirname(f)

    # On trybots, the change being tested is applied directly to the working tree.
    # We should only check if f itself is modified and never inspect HEAD.
    if buildbot.IsTryBot():
        status = proc.check_output(['git', 'status', '--porcelain', f],
                                   cwd=cwd).strip()
        changed = len(status) != 0
        print('%s git status: %s' % (f, status if changed else '(unchanged)'))
        return changed

    # Else find the most recent commit that modified f, and return true if
    # that's the HEAD commit.
    head_rev = GitRevision(cwd)
    last_rev = proc.check_output(
        ['git', 'rev-list', '-n1', 'HEAD', f], cwd=cwd).strip().decode('utf-8')
    print('Last rev modifying %s is %s, HEAD is %s' % (f, last_rev, head_rev))
    return head_rev == last_rev
