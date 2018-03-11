from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import json

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://///var/tmp/names.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db   = SQLAlchemy(app)

class People(db.Model):
    id      = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)

    def __init__(self, name):
        self.name    = name

    def __repr__(self):
        return '<Name %s>' % self.name

db.create_all()


@app.route('/task/<name>', methods=['POST'])
def save_name(name):
    person = People(name)
    db.session.add(person)
    db.session.commit()

    return "{} save into ours database".format(name)

@app.route('/')
def hello():
    people = []

    for person in People.query.all():
        people.append(person.name)
    #return "Hello everyone!"
    
    return json.dumps(people)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
