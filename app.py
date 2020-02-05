from flask import Flask, request

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello, World! - here only for testing\n'

depmap = {}

@app.route("/entry/<namespace>/<k8stype>/<name>", methods = ['POST', 'DELETE'])
def registration(namespace, k8stype, name):
    entries = depmap.get(namespace, [])
    val = "%s/%s" % (k8stype, name)
 
    if request.method == "POST":
        if val not in entries:
           print(val + " added\n")
           entries.append(val)
           depmap[namespace] = entries
        else:
           print(val + " already present\n")
    elif request.method == "DELETE":
       print(val + " removed\n")
       entries.remove(val)

    return "done\n"


@app.route("/list")
def listall():
    return str(depmap)



@app.route("/projects")
def list_projects():
    projects = ""
    for key in depmap:
        print(key)
        projects = projects + key + "\n"
    return projects    



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

