from flask import Flask, jsonify, request, make_response, render_template
from tasks import plant, eat
import random, requests

app = Flask(__name__)

@app.route('/')
def dashboard():
	response = make_response(render_template('dashboard.html'))
	#jsonify({'ip': request.remote_addr, 'cookie': request.cookies.get('cityfarm')})
	response.set_cookie('cityfarm',value='Farmer')
	return response, 200

@app.route('/work', methods=['POST'])
def work():
	if bool(random.getrandbits(1)):
		eat.apply_async(("wheat",), queue='eating', serializer='json', link=get_update())
		eat.apply_async(("corn",), queue='eating', serializer='json', link=get_update())
		return jsonify({'ip': request.remote_addr, 'eat':'citizen'}), 200

	plant.apply_async(["corn"], queue='planting', serializer='json', link=get_update())
	plant.apply_async(["wheat"], queue='planting', serializer='json', link=get_update())
	return jsonify({'ip': request.remote_addr,'plan':'farmer'}), 200


def get_update():
	URL = "http://websocket:8888/update" # set into conf
	r = requests.get(url = URL)
	

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
