import json, names, random, requests 


uri="http://localhost:5000/task/"
for x in range(1,1000):
	name = names.get_full_name()
	url = '{}{}'.format(uri,name)
	#print(url)
	r = requests.post(url)
	#print(dir(r))
	print(r.content)