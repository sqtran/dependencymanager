from flask import Flask, request, render_template
import subprocess
import json
import apppersistence

app = Flask(__name__)
db = apppersistence.Storage()


@app.route('/')
def main_page():
    return render_template('main.html')

# Contracts are returned as a Map [<string>][List<contracts>] as environment (env) to contracts
@app.route("/contracts")
def list_contracts_by_env():
    results = {}
    mapped_contracts = db.select_contracts()
    # mapped_contracts is a map of [namespace][contracts]

    for key in mapped_contracts:
        c = results.get(get_env(key), [])
        c.append(mapped_contracts[key])
        results[get_env(key)] = c

    return json.dumps(results)

@app.route("/providers")
def list_providers():
    mapped = {}
    for i in db.select_controllers():
        if i["deployment_completed"] == 1:
            namespace = i["controller_project"]
            k8s_name_type = "%s/%s" % (i["type"], i["controller_name"])
            provs = i["contracts_provided"]

            tmp = mapped.get(namespace, {})
            tmp[k8s_name_type] = provs
            mapped[namespace] = tmp
    return json.dumps(mapped)

@app.route("/unsatisfied")
def list_unsatisfied_services():
    mapped = {}
    for i in db.select_incomplete_controllers():
        namespace = i["controller_project"]
        k8s_name_type = "%s/%s" % (i["type"], i["controller_name"])
        reqs = i["contracts_required"]

        tmp = mapped.get(namespace, {})
        tmp[k8s_name_type] = reqs
        mapped[namespace] = tmp
    return json.dumps(mapped)

@app.route("/register/<namespace>/<manifest>")
def register_service(namespace, manifest):

    pod_owner = oc_get_owner_reference(namespace, "pod/" + manifest)
    type_name = pod_owner.split("/")
    try:
        owners_owner = oc_get_owner_reference(namespace, pod_owner)
        type_name = owners_owner.split("/")
    except:
        pass

    # Check if this controller already exists in our records
    controller = db.select_controller_by_key(namespace, type_name[0], type_name[1])

    if controller is not None and controller.deployment_completed == 1:
        print("A controller for %s %s %s already exists and is complete" % (namespace, type_name[0], type_name[1]))
        return "This controller is already registered", 200

    deps = get_requires(namespace,  type_name[0], type_name[1])
    contracts = db.select_contracts_by_env(get_env(namespace))
    complete = set(deps).issubset(set(contracts))

    if controller is None:
        print("Need to create a new controller for %s %s %s" % (namespace, type_name[0], type_name[1]))
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


    # If there isn't an ID, then this is new
    if controller.id is None:
        print("Creating the new controller now")
        db.create_controller(controller)
    else:
        print("Updating the existing controller now")
        db.update_controller(controller)

    if complete:
        return "All required dependencies have been satsified", 200
    else:
        print("Required Dependencies %s" %(deps))
        print("Available Contracts %s" %(contracts))
        return "Dependencies are missing", 418


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
