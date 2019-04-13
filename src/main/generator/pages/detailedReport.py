from code.util.db import Submission, User, Contest
from code.generator.lib.htmllib import *
from code.generator.lib.page import *
import logging
from code.util import register
import time

def detailedReport(params, user):
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
    
    problemSummary = {}
    for prob in contest.problems:
        problemSummary[prob.id] = [0, 0]

    scores = []
    for user in subs:
        usersubs = subs[user]
        scor = score(usersubs, start, problemSummary)
        atempts = []
        for i in getDetails(usersubs, contest):
            atempts.append(i)
        scores.append((
            User.get(user).username,
            User.get(user).id,
            scor[0],
            scor[1],
            scor[2],
            atempts
        ))
    scores = sorted(scores, key=lambda score: score[2] * 1000000000 + score[3] * 10000000 - score[4], reverse=True)
    
    ranks = [i + 1 for i in range(len(scores))]
    for i in range(1, len(scores)):
        u1 = scores[i]
        u2 = scores[i - 1]
        if (u1[1], u1[2], u1[3]) == (u2[1], u2[2], u2[3]):
            ranks[i] = ranks[i - 1]

    scoresDisplay = []
    for (name, usrID, solved, samples, points, atempts), rank in zip(scores, ranks):
        atmpts = []
        for atmpt in atempts:
            atmpts.append(h.td(atmpt, cls="center"))
        scoresDisplay.append(h.tr(
            h.td(rank, cls="center"),
            h.td(name) if contest.end <= time.time() * 1000 else '',
            h.td(usrID, cls="center"),
            h.td(solved, cls="center"),
            h.td(points, cls="center"),
            *atmpts
        ))
    problemSummaryDisplay = []
    languageSummaryDisplay = []
    cnt = 1
    for problem in contest.problems:
        contestDict = problem.contests[contest.id]
        problemSummaryDisplay.append(h.tr(
            h.td(cnt),
            h.td(problem.title),
            h.td(problemSummary[problem.id][0], cls="center"),
            h.td(problemSummary[problem.id][1], cls="center")
        ))
        languageSummaryDisplay.append(h.tr(
            h.td(cnt),
            h.td(problem.title),
            h.td(contestDict["c"], cls="center"),
            h.td(contestDict["cpp"], cls="center"),
            h.td(contestDict["cs"], cls="center"),
            h.td(contestDict["java"], cls="center"),
            h.td(contestDict["python2"], cls="center"),
            h.td(contestDict["python3"], cls="center"),
            h.td(contestDict["ruby"], cls="center"),
            h.td(contestDict["vb"], cls="center")
        ))
        cnt += 1

    prblmHeader = []    
    cnt = 1
    for num in contest.problems:
        prblmHeader.append(
        h.th(cnt, cls="center"))
        cnt+=1

    return Page(
        h2("Detailed Report", cls="page-title"),
        h.table(
            h.thead(
                h.tr(
                    h.th("Rank", cls="center"),
                    h.th("Contestant") if contest.end <= time.time() * 1000 else '',
                    h.th("ContestantID", cls="center"),
                    h.th("Correct", cls="center"),
                    h.th("Penalty", cls="center"),
                    *prblmHeader
                )
            ),
            h.tbody(
                *scoresDisplay
            )
        ),
        h2("Problem Summary", cls="page-title"),
        h.table(
            h.thead(
                h.tr(
                    h.th("#"),
                    h.th("Title"),
                    h.th("Attempts", cls="center"),
                    h.th("Correct", cls="center"),
                )
            ),
            h.tbody(
                *problemSummaryDisplay
            )

        ),
        h2("Problem Summary", cls="page-title"),
        h.table(
            h.thead(
                h.tr(
                    h.th("#"),
                    h.th("Title"),
                    h.th("c", cls="center"),
                    h.th("cpp", cls="center"),
                    h.th("cs", cls="center"),
                    h.th("java", cls="center"),
                    h.th("python2", cls="center"),
                    h.th("python3", cls="center"),
                    h.th("ruby", cls="center"),
                    h.th("vb", cls="center")
                )
            ),
            h.tbody(
                *languageSummaryDisplay
            )

        )
    )

def getDetails(submissions: list, contest):
    details = [0] * len(contest.problems)
    index = 0
    for i in contest.problems:
        count = 0
        correct = False

        for j in submissions:
            if j.problem.id == i.id:
                count+=1
                if all(i == "ok" for i in j.results) and not correct:
                    correct = True
                    s, ms = divmod(j.timestamp, 1000)

        tm = time.strftime('%H:%M', time.gmtime(s)) if count and correct else '--'
        tm = '' if count == 0 else tm
        countTxt = '(' + str(count) + ') ' if count else ''
        txt = countTxt + tm
        details[index] = txt
        index += 1
    return details


def score(submissions: list, contestStart, problemSummary) -> tuple:
    
    solvedProbs = 0
    sampleProbs = 0
    penPoints = 0

    # map from problems to list of submissions
    probs = {}

    # Put the submissions into the probs list
    for sub in submissions:
        probId = sub.problem.id
        if probId not in probs:
            probs[probId] = []
        probs[probId].append(sub)
    
    # For each problem, calculate how much it adds to the score
    for prob in probs:
        # Sort the submissions by time
        subs = sorted(probs[prob], key=lambda sub: sub.timestamp)
        # Penalty points for this problem
        points = 0
        solved = False
        sampleSolved = False
        
        for sub in subs:
            for res in sub.results[:sub.problem.samples]:
                if res != "ok":
                    break
            else:
                sampleSolved = True
            if sub.result != "ok":
                # Unsuccessful submissions count for 20 penalty points
                # But only if the problem is eventually solved
                points += 20
            else:
                # The first successful submission adds a penalty point for each
                #     minute since the beginning of the contest
                # The timestamp is in millis
                points += (sub.timestamp - contestStart) // 60000
                solved = True
                break
        
        # Increment attempts
        problemSummary[sub.problem.id][0] += 1

        # A problem affects the score only if it was successfully solved
        if solved:
            solvedProbs += 1
            penPoints += points
            problemSummary[sub.problem.id][1] += 1
        elif sampleSolved:
            sampleProbs += 1
    
    # The user's score is dependent on the number of solved problems and the number of penalty points
    return solvedProbs, sampleProbs, int(penPoints)

register.web("/detailedReport", "loggedin", detailedReport)
