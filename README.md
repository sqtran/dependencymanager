# Dependency Manager


### Motivation

Managing a network of deployments is a tough task, and is not a native feature of Kubernetes... yet.  Whether migrating from monolithic to microservices, or starting from greenfield, there needs to be automation that can determine if a deployment has all its upstream dependencies available.  

Each microservice provides a set of functionality, which will be defined as a contract.  The contract between two microservices is agreed upon in the software development process ahead of time, just like an interface or API is designed.  That contract between the two services is given a unique name (and version), so that prior to deploying an application, Kubernetes can check if that particular contract is available.

This need for automation resulted in this lightweight application called Dependency Manager.

### Architecture

This application is written in `python` with `Flask`, uses `SQLite3` for its backend, and `JQuery` with `bootstrap` on the frontend.

Each application that requires dependency management must register with the dependency manager.  Applications follow the  `Init Container` pattern for registration, by making a call to the registration endpoint.  The dependency manager then checks to see if all dependencies of this application has been fulfilled, and then either returns a successful 200 response, or non-200 if this deployment cannot start.

### Setup

The dependency manager should be installed into a namespace named `depman`.  

```bash
oc create -f depman-bc.yaml
oc create -f depman-sa.yaml
oc create -f depman-is.yaml
oc create -f depman-dc.yaml
oc create -f depman-svc.yaml

#oc create -f ocp-python-bc.yaml
#oc create -f ocp-python-is.yaml
```

The depman serviceaccount needs to be able to pull images from the internal registry.

```bash
oc secrets link depman $(oc get secrets | grep default-dockercfg | awk '{print $1}') --for=pull
```

The dependency manager runs as a `ServiceAccount` named **depman**, which requires cluster-wide view access.

```bash
oc adm policy add-cluster-role-to-user view -z depman -n depman
```

The dependency manager writes its files to a file named `../depmandb/depman.db`.  The directory must exist ahead of time.


### Usage

Using the dependency manager only requires modifying the Kubernetes manifest that deploys your application.  It can be a `Deployment`, `DeploymentConfig`, `StatefulSet`, `ReplicationController`, `ReplicaSet`, or any other manifest object.  Usage requires only two pieces of configuration.

#### 1. Annotations
Each deployment must be annotated with the following.  These fields are comma-separated, and should describe the contracts required and provided by the application.  This belongs in the `.meta.annotations` section of the manifest file.  Note that an empty string in the "requires" annotation means this service does not have any dependencies.

```yaml
gr.depman/provides: "consumerA-producer-1.0, consumerB-producer-0.1, consumerB-producer-0.2"
gr.depman/requires: ""
```
Annotations were chosen over labels because they have more flexibility in terms of character sets.

#### 2. InitContainer
The `initContainer` makes a call to the dependency manager to register its pod name, and its namespace.  The dependency uses these two pieces of information to inspect the Kubernetes objects to determine its controller.

This example uses a simple and lightweight alpine image that includes the `curl` tool, but any image can/will do.  Note that the namespace and the podname are calculated fields, so should not be changed or else registration can be corrupted.
```yaml
      initContainers:
        - name: init-depman
          image: byrnedo/alpine-curl
          command: ["sh", "-c", "curl -f depman.depman.svc.cluster.local:5000/register/$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace)/$HOSTNAME"]
```
It is a goal to provide a prebuilt initContainer that has the proper entrypoint so that registration doesn't require the manual entry of the initContainer's `command`.

### User interface
A simple user interface was created to view the status of managed deployments.  It can be reached on the `:5000` port of the running application, which is dependent on creating a `route` object first.


### Local Development
There is tight integration with `Openshift` at the moment, so local development will either require access to a running cluster or setting up Minishift/CRC.  A lot of the backend functionality run `oc` commands to inspect different Kubernetes objects.
