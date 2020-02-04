from flask import Flask
app = Flask(__name__)

PORT = int(os.environ.get('OPENSHIFT_PYTHON_PORT', 8080))

@app.route('/')
def hello_world():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
