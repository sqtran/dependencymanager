from app import app

print("initiated the app! With a name of:", __name__)

depmap = {}

@app.route('/')
@app.route('/index')
def index():
    return "Hello, World!"


@app.route('/msg/<key>/<message>')
def withargs(key, message):
    if message is not None and key is not None:
        print("key[%s] = %s" %(key, message))
        depmap[key] = message
    else:
        print("no message passed")
    return "item added"

@app.route('/getDependencies')
def getDependencies():
    print(str(depmap))
    return str(depmap)


@app.route('/register')
def register():
    out = subprocess.Popen(['ls', '-latrh', '/tmp'],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT)
    stdout,stderr = out.communicate()
    print(stdout)
    print(stderr)
    return "registered something"
