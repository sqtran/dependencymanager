from flask import Flask, request
import subprocess

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


@app.route("/dependencyCheck/<namespace>/<k8stype>/<name>")
def check_dependencies(namespace, k8stype, name):
   #"oc get dc spring-boot-git -o jsonpath={.metadata.labels}"

   cmd = "oc get %s/%s -n %s -o jsonpath={.metadata.labels}" % (k8stype, name, namespace)

   # returns output as byte string
   returned_output = subprocess.check_output(cmd)
   print('results is:', returned_output.decode("utf-8"))

   return returned_output.decode("utf-8")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

