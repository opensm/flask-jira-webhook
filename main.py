from flask import Flask

app = Flask(__name__)


@app.route('/jira_webhook')
def hello_world(**kwargs):
    print(kwargs)
    return 'Hello World!'


if __name__ == '__main__':
    app.run()
