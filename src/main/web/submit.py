import os
import logging
from code.util import register
from code.util.db import Submission, Problem, User
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
    if os.system(f"docker run --rm --network=none -m 256MB -v /tmp/{sub.id}/:/source nathantheinventor/open-contest-dev-{sub.language}-runner {tests} 5 > /tmp/{sub.id}/result.txt") != 0:
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
        if res == "ok" and strip((answers[-1] or "").rstrip()) != strip((outputs[-1] or "").rstrip()):
            res = "wrong_answer"
        if res == None:
            res = "tle"
        results.append(res)

        # Make result the first incorrect result
        if res != "ok" and result == "ok":
            result = res

    sub.result = result
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

    if sub.type == "submit":
        sub.save()

    shutil.rmtree(f"/tmp/{sub.id}", ignore_errors=True)

def submit(params, setHeader, user):
    probId = params["problem"]
    lang   = params["language"]
    code   = params["code"]
    type   = params["type"]
    submission = addSubmission(probId, lang, code, user, type)
    runCode(submission)
    return submission.toJSON()

def changeResult(params, setHeader, user):
    id = params["id"]
    sub = Submission.get(id)
    if not sub:
        return "Error: incorrect id"
    sub.result = params["result"]
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
