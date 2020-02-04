from flask import Flask

app = Flask(__name__)

if __name__ == '__main__':
    app.run(use_reloader=True)

from app import routes
