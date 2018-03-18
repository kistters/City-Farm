from tasks import eat

for x in range(5):
	eat.apply_async(('corn',3), queue='eating', serializer='json')
	eat.apply_async(('wheat',50), queue='eating', serializer='json')
