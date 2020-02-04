from flask import Flask, request
from kubernetes import client, config
from openshift.dynamic import DynamicClient


app = Flask(__name__)


k8s_client = config.new_client_from_config()
dyn_client = DynamicClient(k8s_client)

v1_projects = dyn_client.resources.get(api_version='project.openshift.io/v1', kind='Project')

project_list = v1_porjects.get()

for project in project_list.items:
    print(project.metadata.name)



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
    



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

