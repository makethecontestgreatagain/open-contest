import os
import logging
from code.util import register
from code.util.db import Submission, Problem, User, Contest
import time
import shutil
import re
from uuid import uuid4

def addSubmission(probId, lang, code, user, type):
    sub = Submission()
    sub.problem = Problem.get(probId)
    sub.language = lang
    sub.code = code
    sub.result = "pending"
    sub.user = user
    sub.timestamp = time.time() * 1000
    sub.type = type
    sub.status = "Review"
    if type == "submit":
        sub.save()
    else:
        sub.id = str(uuid4())
    return sub

exts = {
    "c": "c",
    "cpp": "cpp",
    "cs": "cs",
    "java": "java",
    "python2": "py",
    "python3": "py",
    "ruby": "rb",
    "vb": "vb"
}

def readFile(path):
    try:
        with open(path, "rb") as f:
            return f.read(1000000).decode("utf-8")
    except:
        return None

def strip(text):
    return re.sub("[ \t\r]*\n", "\n", text)

def runCode(sub):
    # Copy the code over to the runner /tmp folder
    extension = exts[sub.language]
    os.mkdir(f"/tmp/{sub.id}")
    with open(f"/tmp/{sub.id}/code.{extension}", "wb") as f:
        f.write(sub.code.encode("utf-8"))
    
    prob = sub.problem
    tests = prob.samples if sub.type == "test" else prob.tests
    
    # Copy the input over to the tmp folder for the runner
    for i in range(tests):
        shutil.copyfile(f"/db/problems/{prob.id}/input/in{i}.txt", f"/tmp/{sub.id}/in{i}.txt")

    # Output files will go here
    os.mkdir(f"/tmp/{sub.id}/out")

    # Run the runner
    if os.system(f"docker run --rm --network=none -m 256MB -v /tmp/{sub.id}/:/source nathantheinventor/open-contest-dev-{sub.language}-runner {tests} {prob.timeLimit} > /tmp/{sub.id}/result.txt") != 0:
        raise Exception("Something went wrong")

    inputs = []
    outputs = []
    answers = []
    errors = []
    results = []
    result = "ok"

    for i in range(tests):
        inputs.append(sub.problem.testData[i].input)
        errors.append(readFile(f"/tmp/{sub.id}/out/err{i}.txt"))
        outputs.append(readFile(f"/tmp/{sub.id}/out/out{i}.txt"))
        answers.append(sub.problem.testData[i].output)
        
        res = readFile(f"/tmp/{sub.id}/out/result{i}.txt")
        stripOutput = strip((outputs[-1] or "").rstrip())
        stripAnswers = strip((answers[-1] or "").rstrip())
        extraRE = re.sub(r"\n", r"\n(?:[^\n]*\n)?", stripAnswers) + r".*"
        incompleteRE = "(?:" + re.sub(r"\n", r"\n)?(", stripAnswers) + ")?"
        if res == "ok" and stripAnswers != stripOutput:
            if re.fullmatch(incompleteRE, stripOutput, re.DOTALL) or stripAnswers.startswith(stripOutput):
                res = "incomplete_output"
            elif re.fullmatch(extraRE, stripOutput, re.DOTALL):
                res = "extra_output"
            else:
                res = "wrong_answer"
        if res == None:
            res = "tle"
        results.append(res)

        # Make result the first incorrect result
        if res != "ok" and result == "ok":
            result = res

    sub.result = result
    if sub.result in ["ok", "runtime_error", "tle"]:
        sub.status = "Judged"
    if readFile(f"/tmp/{sub.id}/result.txt") == "compile_error\n":
        sub.results = "compile_error"
        sub.delete()
        sub.compile = readFile(f"/tmp/{sub.id}/out/compile_error.txt")
        shutil.rmtree(f"/tmp/{sub.id}", ignore_errors=True)
        return

    sub.results = results
    sub.inputs = inputs
    sub.outputs = outputs
    sub.answers = answers
    sub.errors = errors
    contestDict = sub.problem.contests[Contest.getCurrent().id]
    if all(i == "ok" for i in results) and sub.user.id not in contestDict["completed"]:
        contestDict["completed"].append(sub.user.id)
        if sub.language == 'c':
            contestDict["c"] += 1
        elif sub.language == 'cpp':
            contestDict["cpp"] += 1
        elif sub.language == 'cs':
            contestDict["cs"] += 1
        elif sub.language == 'java':
            contestDict["java"] += 1
        elif sub.language == 'python2':
            contestDict["python2"] += 1
        elif sub.language == 'python3':
            contestDict["python3"] += 1
        elif sub.language == 'ruby':
            contestDict["ruby"] += 1
        elif sub.language == 'vb':
            contestDict["vb"] += vb

    if sub.type == "submit":
        sub.save()
        sub.problem.save()

    shutil.rmtree(f"/tmp/{sub.id}", ignore_errors=True)

def submit(params, setHeader, user):
    probId = params["problem"]
    lang   = params["language"]
    code   = params["code"]
    type   = params["type"]
    submission = addSubmission(probId, lang, code, user, type)
    runCode(submission)
    response = submission.toJSON()
    if submission.type != "test":
        response["result"] = submission.getContestantResult()
        response["results"] = submission.getContestantIndividualResults()
    return response

def changeResult(params, setHeader, user):
    version = int(params["version"])
    id = params["id"]
    sub = Submission.get(id)
    contestDict = sub.problem.contests[Contest.getCurrent().id]

    scoreChange = -1 if params["result"] != "ok" else 1
    if (sub.user.id in contestDict["completed"] and scoreChange == -1) or (sub.user.id not in contestDict["completed"] and scoreChange == 1):
        if scoreChange == -1:
            contestDict["completed"].remove(sub.user.id)
        else:
            contestDict["completed"].append(sub.user.id)

        if sub.language == 'c':
            contestDict['c'] += scoreChange
        elif sub.language == 'cpp':
            contestDict['cpp'] += scoreChange
        elif sub.language == 'cs':
            contestDict['cs'] += scoreChange
        elif sub.language == 'java':
            contestDict['java'] += scoreChange
        elif sub.language == 'python2':
            contestDict['python2'] += scoreChange
        elif sub.language == 'python3':
            contestDict['python3'] += scoreChange
        elif sub.language == 'ruby':
            contestDict['ruby'] += scoreChange
        elif sub.language == 'vb':
            contestDict['vb'] += scoreChange
    if not sub:
        return "Error: incorrect id"
    elif sub.version != version:
        return "The submission has been changed by another judge since you loaded it. Please reload the sumbission to modify it."
    sub.result = params["result"]
    sub.status = params["status"]
    sub.version += 1
    sub.checkout = None
    sub.save()
    return "ok"

def rejudge(params, setHeader, user):
    id = params["id"]
    submission = Submission.get(id)
    if os.path.exists(f"/tmp/{id}"):
        shutil.rmtree(f"/tmp/{id}")
    runCode(submission)
    return submission.result

def rejudgeAll(params, setHeader, user):
    probId = params["probId"]
    # curTime = params["curTime"]
    curTime = time.time() * 1000
    count = 0
    for contestant in filter(lambda c: not c.isAdmin(), User.all()):
        for sub in filter(lambda s: s.user.id == contestant.id and s.problem.id == probId and s.timestamp < curTime and s.result != "reject" and s.type != "test", Submission.all()):
            if os.path.exists(f"/tmp/{id}"):
                shutil.rmtree(f"/tmp/{id}")
            runCode(sub)
            count += 1
    return {"name": Problem.get(probId).title, "count": count}

register.post("/submit", "loggedin", submit)
register.post("/changeResult", "admin", changeResult)
register.post("/rejudge", "admin", rejudge)
register.post("/rejudgeAll", "admin", rejudgeAll)
