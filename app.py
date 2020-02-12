from flask import Flask, request, render_template
import subprocess
import json

app = Flask(__name__)

@app.route('/')
def main_page():
    return render_template('main.html')


# Contracts are stored as [<string>][List<contracts>] as environment (env) to contracts
contracts = {}

# Providers are stored as [<string>][[<string>][List<string>]] as namespace to k8s_objects to contracts
providers = {}

missing_dependencies = {}

@app.route("/test/<namespace>/<k8s>/<name>/<contract>", methods = ['POST', 'DELETE'])
def test_method_only(namespace, k8s, name, contract):
    env = get_env(namespace)
    entries = contracts.get(env, [])

    ns_to_type = providers.get(namespace, {})
    provs = ns_to_type.get("%s/%s" % (k8s, name), [])

    if request.method == "POST":
        if contract not in entries:
            entries.append(contract)
            print(contract + " added\n")
        if contract not in provs:
            provs.append(contract)
    elif request.method == "DELETE":
       entries.remove(contract)
       provs.remove(contract)
       print(contract + " removed\n")

    ns_to_type["%s/%s" % (k8s, name)] = provs

    providers[namespace] = ns_to_type
    contracts[env] = entries
    return "done\n"

@app.route("/contracts")
def list_contracts():
    return json.dumps(contracts)

@app.route("/providers")
def list_providers():
    return json.dumps(providers)

@app.route("/flush", methods = ['POST'])
def flush():
    contracts = {}
    providers = {}
    missing_dependencies = {}
    return "flushed"

# TODO add a mechanism to loop through and refresh the provides/requires for all known components
@app.route("/refresh")
def refresh():
    return "refreshened"

@app.route("/envs")
def list_envs():
    envs = ""
    for key in contracts:
        print(key)
        envs = envs + key + "\n"
    return envs

@app.route("/register/<namespace>/<manifest>")
def register_service(namespace, manifest):
    pod_owner = oc_get_owner_reference(namespace, "pod/" + manifest)
    owners_owner = oc_get_owner_reference(namespace, pod_owner)

    ref = owners_owner
    if owners_owner is None:
        print("no owner, this is either a ReplicaSet or ReplicationController so there's nothing left to do")
        ref = pod_owner

    return dependency_check(namespace, ref.split("/")[0], ref.split("/")[1])

# TODO

# 1)  get ownerReference by pod name and Namespace to get ReplicationController or ReplicaSets
# 2)  lookup replicacontrollr or replicasets to determine if there is a Deployment, DeploymentConfig, or StatefulSet owner to follow, otherwise it's just RS or RC


# TODO need k8s type validation
@app.route("/dependencyCheck/<namespace>/<k8stype>/<name>")
def dependency_check(namespace, k8stype, name):

   if dependencies_satisified(namespace, k8stype, name):
       add_contracts(namespace, k8stype, name)
       missing_dependencies.get(namespace, {}).pop("%s/%s" % (k8stype, name), [])
       return "All good!", 200
   else:
       return "Dependencies are missing", 418
       ## TODO this could return a smarter list of the individual pieces missing


@app.route("/missing")
def get_missing_dependencies():
    return json.dumps(missing_dependencies)
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
                 ns_to_type = missing_dependencies.get(namespace, {})
                 missing = ns_to_type.get("%s/%s" %(k8stype, name), [])

                 if k.strip() not in missing:
                     missing.append(k.strip())
                     ns_to_type["%s/%s" % (k8stype, name)] = missing
                     missing_dependencies[namespace]  = ns_to_type

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
            add_provider(namespace, k8stype, name, k)

# Add contract provider to our map
def add_provider(namespace, k8stype, name, contract):
    key = "%s/%s" % (k8stype, name)
    ns_to_type = providers.get(namespace, {})
    contracts = ns_to_type.get(key, [])

    if contract not in contracts:
        contracts.append(contract)

    ns_to_type[key] = contracts
    providers[namespace] = ns_to_type

# if namespace does not have a hypen in it, it just defaults to the name of the namespace
def get_env(namespace):
    return namespace.split("-")[-1]

def get_oc_output(cmd):
    return subprocess.check_output(cmd, shell=True).decode("utf-8")
9
def oc_get_owner_reference(namespace, object):
    kind = get_oc_output("oc get %s -n %s -o go-template='{{ (index .metadata.ownerReferences 0).kind }}'" % (object, namespace))
    name = get_oc_output("oc get %s -n %s -o go-template='{{ (index .metadata.ownerReferences 0).name }}'" % (object, namespace))
    return "%s/%s" % (kind, name)

# runs an OC command to grab a label
def oc_get_labels_str(namespace, k8stype, name, field):
    return get_oc_output("oc get %s/%s -n %s -o go-template='{{ index .metadata.annotations \"%s\"}}'" % (k8stype, name, namespace, field))

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
