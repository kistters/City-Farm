from tasks import plant

for x in range(10):
	plant.apply_async(('corn',10), queue='planting', serializer='json')
	plant.apply_async(('wheat',90), queue='planting', serializer='json')

# for idx, item in enumerate(items):
