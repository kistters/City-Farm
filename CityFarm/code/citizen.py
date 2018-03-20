from tasks import eat

for x in range(5):
	eat.apply_async(("corn",), queue='eating', serializer='json')
	eat.apply_async(("wheat",), queue='eating', serializer='json')
