from flask import Flask, request, render_template
import subprocess
import json
import apppersistence

app = Flask(__name__)
db = apppersistence.Storage()


@app.route('/')
def main_page():
    return render_template('main.html')

# Contracts are stored as [<string>][List<contracts>] as environment (env) to contracts
contracts = {}
# Providers are stored as [<string>][[<string>][List<string>]] as namespace to k8s_objects to contracts
providers = {}
missing_dependencies = {}


## Testing only - delete when done
@app.route("/testp")
def testp():
    #obj = apppersistence.Storage()
    return db.printhello()

## Testing only - delete when done
@app.route("/testfa")
def testfa():
    return json.dumps(db.select_controllers())

## Testing only - delete when done
@app.route("/testf/<id>")
def testf(id):
    return json.dumps(db.select_controller_by_id(id))

## Testing only - delete when done
@app.route("/testd/<id>")
def testd(id):
    db.delete_controller_by_id(id)
    return "deleted "

@app.route("/testu/<id>")
def testu(id):
    controller = apppersistence.Workload_Controller()
    controller.microservice_name = "updated"                      # pull from annotation
    controller.microservice_api_version = "updated"               # pull from annotation
    controller.microservice_artifact_version = "updated"          # pull from annotation
    controller.contracts_provided = "provided"
    controller.contracts_required = "required"
    controller.deployment_completed = True
    controller.id = id
    db.update_controller(controller)
    return "done"

## Testing only - delete when done
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


# Contracts are stored as [<string>][List<contracts>] as environment (env) to contracts
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
    type_name = pod_owner.split("/")
    try:
        owners_owner = oc_get_owner_reference(namespace, pod_owner)
        type_name = owners_owner.split("/")
    except:
        pass

    # Check if this controller is already exists in our records
    controller = db.select_controller_by_key(namespace,  type_name[0], type_name[1])

    if controller is not None and controller["deployment_completed"]:
        print("A controller for %s %s %s already exists and is complete" % (namespace, type_name[0], type_name[1]))
        return "This controller is already registered", 200
    else:
        print("No controller found for %s %s %s, this is a new service to register" % (namespace, type_name[0], type_name[1]))

    deps = get_requires(namespace,  type_name[0], type_name[1])
    contracts = db.select_contracts_by_env(get_env(namespace))
    complete = set(deps).issubset(set(contracts))

    print("This controller requires the following contracts")
    print(deps)

    if controller is None:
        print("Creating a new controller for %s %s %s" % (namespace, type_name[0], type_name[1]))
        controller = apppersistence.Workload_Controller()
        controller.type = type_name[0]
        controller.controller_name = type_name[1]
        controller.controller_project = namespace

    controller.microservice_name = "ms name"                              # pull from annotation
    controller.microservice_api_version = "ms api version"                # pull from annotation
    controller.microservice_artifact_version = "ms artifact version"      # pull from annotation
    controller.contracts_provided = ",".join(get_provides(namespace, type_name[0], type_name[1]))
    controller.contracts_required = ",".join(deps)
    controller.deployment_completed = complete


    if controller is None:
        print("Creating the new controller now")
        db.create_controller(controller)
    else:
        print("Updating required contracts to %s" % (controller.contracts_required))
        print("Updating provided contracts to %s" % (controller.contracts_provided))
        db.update_controller(controller)

    if complete:
        return "All required dependencies have been satsified", 200
    else:
        print("Required Dependencies %s" %(deps))
        print("Provided Dependencies %s" %(contracts))
        return "Dependencies are missing", 418

# TODO delete this, this isn't required
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
    if my_str_list is None or my_str_list == "":
        return []
    else:
        sanitized = []
        for k in my_str_list.split(","):
            if k.strip() not in sanitized:
                sanitized.append(k.strip())
        return sanitized

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
