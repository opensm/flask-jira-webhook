from flask import Flask, request

app = Flask(__name__)


@app.route('/jira_webhook', methods=["POST"])
def hello_world():
    print(request.form)
    return 'Hello World!'


if __name__ == '__main__':
    app.run(host='0.0.0.0')
