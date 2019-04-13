from code.util import register
from code.util.db import Contest, Problem
import json

def deleteContest(params, setHeader, user):
    id = params["id"]
    contest = Contest.get(id)
    for i in contest.problems:
        del i.contests[contest.id]
        i.save()
    contest.delete()
    return "ok"

def editContest(params, setHeader, user):
    id = params.get("id")
    contest = Contest.get(id) or Contest()

    contest.name     = params["name"]
    contest.start    = int(params["start"])
    contest.end      = int(params["end"])
    contest.scoreboardOff = int(params["scoreboardOff"])
    contest.probInfoBlocks = params["probInfoBlocks"] == "True"
    contest.problems = [Problem.get(id) for id in json.loads(params["problems"])]
    for i in contest.problems:
        i.contests[contest.id] = {"c" : 0, "cpp" : 0, "cs" : 0, "java" : 0, "python2" : 0, "python3" : 0, "ruby" : 0, "vb" : 0, "completed" : []}
        i.save()
    if str(params["tieBreaker"]).lower() == "true":
        contest.tieBreaker = True
    else:
        contest.tieBreaker = False
    contest.save()

    return contest.id

register.post("/deleteContest", "admin", deleteContest)
register.post("/editContest", "admin", editContest)
