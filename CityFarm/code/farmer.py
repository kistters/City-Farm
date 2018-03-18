from tasks import plant

for x in range(10):
	plant.apply_async(('corn',3), queue='planting', serializer='json')
	plant.apply_async(('wheat',10), queue='planting', serializer='json')

# for idx, item in enumerate(items):
