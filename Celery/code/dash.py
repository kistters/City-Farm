from flask import Flask, jsonify, render_template
import redis, json

app = Flask(__name__)

redisDb = redis.StrictRedis(host='redis', port=6379, db=0)


@app.route('/farm')
#@crossdomain(origin='*')
def hello_world():
	data = {
		    'milho': redisDb.get('milho').decode('utf-8'),
		    'trigo': redisDb.get('trigo').decode('utf-8')
		}

	response = jsonify(data)
	response.headers.add('Access-Control-Allow-Origin', '*')
	return response
	
if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
