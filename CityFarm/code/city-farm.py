from flask import Flask, jsonify, request, make_response
from tasks import plant, eat
import random


app = Flask(__name__)

@app.route('/')
def home():
	response = make_response(jsonify({'ip': request.remote_addr, 'cookie': request.cookies.get('cityfarm')}))
	response.set_cookie('cityfarm',value='Farmer')
	return response, 200


@app.route('/work', methods=['POST'])
def work():
	if bool(random.getrandbits(1)):
		eat.apply_async(("wheat",), queue='eating', serializer='json')
		eat.apply_async(("corn",), queue='eating', serializer='json')
		return jsonify({'ip': request.remote_addr, 'eat':'citizen'}), 200

	plant.apply_async(["corn"], queue='planting', serializer='json')
	plant.apply_async(["wheat"], queue='planting', serializer='json')
	return jsonify({'ip': request.remote_addr,'plan':'farmer'}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
