from flask import Flask, request
import subprocess

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello, World! - here only for testing\n'

depmap = {}
contracts = {}

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
def dependencyCheck(namespace, k8stype, name):
  
   if dependencies_satisified(namespace, k8stype, name):
       add_contracts(namespace, k8stype, name)
       return "Complete"
   else:
       return "Incomplete"
       ## TODO this could return a smarter list of the individual pieces missing


# 
def dependencies_satisifed(namespace, k8stype, name):
    satisifed = true
    deps = get_requires(namespace, k8stype, name)
    env = get_env(namespace)

    if len(deps) > 0:
        for k in dep:
        # check if our contract dependency is available
             if k not in contracts[env]:
                 print("This service is missing a contract dependency on %s " % (k))
                 satisified = false
                 break
    else:
        print("No dependencies, we're good to start")
 
    return satisifed

# Add provided contracts to our map
def add_contracts(namespace, k8stype, name):
    provs = get_provides(namespace, k8stype, name)
    env = get_env(namespace)
    for k in provs:
        if contracts[env] is None:
            contracts[env] = []
        if k not in contracts[env]:
            print("adding %s to our known contracts" % (k))
            contracts[env].append(k)


# TODO this should be safer
def get_env(namespace):
    return namespace.split("-")[1]


# runs an OC command to grab a label
def oc_get_labels_str(namespace, k8stype, name, label):
    cmd = "oc get %s/%s -n %s -o go-template='{{ index .metadata.labels \"%s\"}}'" % (k8stype, name, namespace, label)
    val = subprocess.check_output(cmd, shell=True).decode("utf-8")
    return val


# returns a list of contracts being provided
def get_provides(namespace, k8stype, name):
    return sanitize_list(oc_get_labels_str(namespace, k8stype, name, "gr.depman/provides"))


# returns a list of contracts required
def get_requires(namespace, k8stype, name):
    return sanitize_list(oc_get_labels_str(namespace, k8stype, name, "gr.depman/requires"))


def sanitize_list(my_str_list):
    if my_str_list is None:
        return []
    else:
        sanitized = []
        for k in my_str_list.split(","):
            if k.strip() not in sanitized:
                sanitized.append(k.strip())
        return sanitized

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

