import os
from flask import Flask

PORT = int(os.environ.get('OPENSHIFT_PYTHON_PORT', 8080))

app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'Hello, World! app.py'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
