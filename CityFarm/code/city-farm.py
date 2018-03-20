from flask import Flask
import random


app = Flask(__name__)

@app.route('/')
def tasks_list():
    if bool(random.getrandbits(1)):
        return "Hello Farmer!"

    return "Hello Citizen!"

@app.route('/work', methods=['POST'])
def add_task():
    return "Go go!"

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
