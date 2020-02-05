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
   label = "gr.depman/requires"
   cmd = "oc get %s/%s -n %s -o go-template='{{ index .metadata.labels \"%s\"}}'" % (k8stype, name, namespace, label)

   ret_val = subprocess.check_output(cmd, shell=True)  # returns the exit code in unix

   # split ret_val by comma delimiter,  trim pieces, compare with a map of provided dependencies

   print('returned value:', ret_val)
   print("dependencies = " + str(ret_val["gr.depman/requires"]))

   return str(ret_val)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

