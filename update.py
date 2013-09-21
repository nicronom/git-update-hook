#!/usr/local/bin/python
# coding: utf-8
import re
import sys
import string
import subprocess


AVAILABLE_ACTIONS = "feature|fix|docs|style|refactor|test|temp|maintain|Merge"
REF_EMPTY = "0000000000000000000000000000000000000000"

MESSAGE_RULES = "There are errors in commit messages. See [url] for details.\n"
MESSAGE_LINE = "  Line {}: {}"

COMMAND_PROJECT_NAME = "git config project.name"
COMMAND_COMMIT_MESSAGE = "git cat-file commit {} | sed '1,/^$/d'"
COMMAND_LIST = "git rev-list {}..{}"
COMMAND_FOR_EACH = "git for-each-ref --format='%(objectname)' 'refs/heads/*'"
COMMAND_LOG = "git log {} --pretty=%H --not {}"

REASON_NOT_BLANK = "Must be blank"
REASON_TOO_LONG = "Too long"
REASON_FORMAT = "Bad format"

LENGTH_MAX = 80
LENGTH_MAX_FIRST = 100


def runBash(commandLine):
    process = subprocess.Popen(commandLine, shell=True, stdout=subprocess.PIPE)
    out = process.stdout.read().strip()
    return out


def getLineErrorMessage(number, reason):
    return MESSAGE_LINE.format(str(number), reason)


def getProjectName():
    return runBash(COMMAND_PROJECT_NAME)


def checkCommit(hash):
    commitMessage = runBash(COMMAND_COMMIT_MESSAGE.format(hash))
    return checkMessage(commitMessage)


def checkMessage(message):
    result = {"errors": [], "ok": True}
    number = 1
    lines = message.split("\n")
    for line in lines:
        if number == 1:
            checkResult = checkFirstLine(line)
            result["ok"] = checkResult["ok"]
            result["errors"].extend(checkResult["errors"])
        elif number == 2:
            if len(line) > 0:
                result["ok"] = False
                result["errors"].append(
                    getLineErrorMessage(number, REASON_NOT_BLANK)
                )
        else:
            if len(line.decode("utf-8")) > LENGTH_MAX:
                result["ok"] = False
                result["errors"].append(
                    getLineErrorMessage(number, REASON_TOO_LONG)
                )
        number = number + 1
    return result


def checkFirstLine(line):
    result = {"ok": True, "errors": []}
    expression = r"^({0}\-\d+ )?({1})(\/({1}))* .*".format(
        getProjectName(), AVAILABLE_ACTIONS
    )
    if not re.match(expression, line):
        result["ok"] = False
        result["errors"].append(getLineErrorMessage(1, REASON_FORMAT))
    if len(line.decode("utf-8")) > LENGTH_MAX_FIRST:
        result["ok"] = False
        result["errors"].append(getLineErrorMessage(1, REASON_TOO_LONG))
    return result


def main():
    ref = sys.argv[1]
    refOld = sys.argv[2]
    revNew = sys.argv[3]
    # if new branch is pushing
    if refOld == REF_EMPTY:
        headList = runBash(COMMAND_FOR_EACH)
        heads = headList.replace(ref + "\n", "").replace("\n", " ")
        commits = runBash(COMMAND_LOG.format(revNew, heads)).split("\n")
    else:
        commits = runBash(COMMAND_LIST.format(refOld, revNew)).split("\n")
    ok = True
    results = []
    for commit in commits:
        # if new branch is pushing without any commits
        if len(commit) == 0:
            sys.exit(0)
        result = checkCommit(commit)
        result["hash"] = commit
        results.append(result)
        ok = ok and result["ok"]
    if not ok:
        print MESSAGE_RULES
        for result in results:
            if not result["ok"]:
                print "Commit {}:\n{}\n".format(
                    result["hash"], string.join(result["errors"], "\n")
                )
        return 1
    else:
        return 0

if __name__ == "__main__":
    sys.exit(main())
