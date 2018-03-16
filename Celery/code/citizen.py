from tasks import comerMilho, comerTrigo

for x in range(1000):
	comerMilho.apply_async(queue='milho.comer', serializer='json')
	comerTrigo.apply_async(queue='trigo.comer', serializer='json')
