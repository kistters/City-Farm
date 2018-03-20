from tasks import plant

for x in range(10):
	#plant.apply_async(("corn",), queue='planting', serializer='json')
	#plant.apply_async(("wheat",), queue='planting', serializer='json')
	plant.apply_async(["corn"], queue='planting', serializer='json')
	plant.apply_async(["wheat"], queue='planting', serializer='json')

# for idx, item in enumerate(items):
