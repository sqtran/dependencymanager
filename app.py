from flask import Flask, request
import subprocess

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello, World! - here only for testing\n'

# Contracts are stored as [<string>][List<contracts>] as environment (env) to contracts
contracts = {}

@app.route("/test/<namespace>/<contract>", methods = ['POST', 'DELETE'])
def test_method_only(namespace, contract):
    env = get_env(namespace)
    entries = contracts.get(env, [])
 
    if request.method == "POST":
        if contract not in entries:
            entries.append(contract)
            print(contract + " added\n")
    elif request.method == "DELETE":
       entries.remove(contract)
       print(contract + " removed\n")

    contracts[env] = entries
    return "done\n"


@app.route("/contracts")
def list_contracts():
    return str(contracts)


@app.route("/envs")
def list_envs():
    envs = ""
    for key in contracts:
        print(key)
        envs = envs + key + "\n"
    return envs    


@app.route("/dependencyCheck/<namespace>/<k8stype>/<name>")
def dependencyCheck(namespace, k8stype, name):
  
   if dependencies_satisified(namespace, k8stype, name):
       add_contracts(namespace, k8stype, name)
       return "All good!", 200
   else:
       return "Dependencies are missing", 408
       ## TODO this could return a smarter list of the individual pieces missing


# 
def dependencies_satisified(namespace, k8stype, name):
    fulfilled = True
    deps = get_requires(namespace, k8stype, name)
    env = get_env(namespace)

    # if we have more than 1 dependency, or if we only have 1 and it's not blank
    if len(deps) > 1 or (len(deps) == 1 and deps[0].strip() != ""):
        for k in deps:
        # check if our contract dependency is available
             if env not in contracts or k not in contracts[env]:
                 print("This service is missing a contract dependency on %s " % (k))
                 fulfilled = False
                 break
    else:
        print("No dependencies, we're good to start")
 
    return fulfilled

# Add provided contracts to our map
def add_contracts(namespace, k8stype, name):
    provs = get_provides(namespace, k8stype, name)
    env = get_env(namespace)
    for k in provs:
        if env not in contracts:
            contracts[env] = []
        if k not in contracts[env]:
            print("adding %s to our known contracts" % (k))
            contracts[env].append(k)

# if namespace does not have a hypen in it, it just defaults to the name of the namespace
def get_env(namespace):
    return namespace.split("-")[-1]


# runs an OC command to grab a label
def oc_get_labels_str(namespace, k8stype, name, field):
    cmd = "oc get %s/%s -n %s -o go-template='{{ index .metadata.annotations \"%s\"}}'" % (k8stype, name, namespace, field)
    val = subprocess.check_output(cmd, shell=True).decode("utf-8")
    return val


# returns a list of contracts being provided
def get_provides(namespace, k8stype, name):
    return sanitize_list(oc_get_labels_str(namespace, k8stype, name, "gr.depman/provides"))


# returns a list of contracts required
def get_requires(namespace, k8stype, name):
    return sanitize_list(oc_get_labels_str(namespace, k8stype, name, "gr.depman/requires"))


def sanitize_list(my_str_list):
    if my_str_list is None or my_str_list == "<no value>":
        return []
    else:
        sanitized = []
        for k in my_str_list.split(","):
            if k.strip() not in sanitized:
                sanitized.append(k.strip())
        return sanitized

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

