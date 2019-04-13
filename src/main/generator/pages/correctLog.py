from code.util.db import Submission, User, Contest
from code.generator.lib.htmllib import *
from code.generator.lib.page import *
import logging
from operator import itemgetter
from code.util import register
import time
import operator

def correctLog(params, user):
    contest = Contest.getCurrent() or Contest.getPast()
    if not contest:
        return Page(
            h1("&nbsp;"),
            h1("No Contest Available", cls="center")
        )
    elif contest.scoreboardOff <= time.time() * 1000 and not user.isAdmin():
        return Page(
            h1("&nbsp;"),
            h1("Scoreboard is off.", cls="center")
        )

    start = contest.start
    end = contest.end

    subs = {}
    for sub in Submission.all():
        if start <= sub.timestamp <= end and not sub.user.isAdmin():
            subs[sub.user.id] = subs.get(sub.user.id) or []
            subs[sub.user.id].append(sub)            


    log = createLog(subs)
    
    logDisplay = []
    for (tmstmp, usr, ttl, id) in log:
        logDisplay.append(h.tr(
            h.td(tmstmp, cls='time-format', data_timestamp=tmstmp),
            h.td(usr),
            h.td(ttl, cls="center"),
        ))

    return Page(
        h2("Correct Log", cls="page-title"),
        h.table(
            h.thead(
                h.tr(
                    h.th("Date/Time", cls="center"),
                    h.th("Contestant"),
                    h.th("Problem", cls="center")
                )
            ),
            h.tbody(
                *logDisplay
            )
        )
    )

def createLog(submissions: list) -> tuple:
    """ Given a list of submissions by a particular user, calculate that user's score.
        Calculates score in ACM format. """

    # map from problems to list of submissions
    log = []

    for user in submissions:
        usersubs = submissions[user]
        # Put the submissions into the probs list
        for sub in usersubs:
            if all(i == "ok" for i in sub.results):
                foundMatch = False

                for (j, k, l, m) in log:
                    if k == User.get(user).username and m == sub.problem.id and j < sub.timestamp:
                        foundMatch = True
                        break
                    elif k == User.get(user).username and m == sub.problem.id and j > sub.timestamp:
                        foundMatch = False
                        log.remove((j,k,l,m))
                        break

                if not foundMatch:
                    temp = (sub.timestamp, User.get(user).username, sub.problem.title, sub.problem.id)
                    log.append(temp)       

    log.sort(key = operator.itemgetter(0), reverse=True)
    print(log)
    return log

register.web("/correctLog", "loggedin", correctLog)
