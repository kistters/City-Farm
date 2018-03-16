from tasks import plantarMilho, plantarTrigo

for x in range(100):
	plantarMilho.apply_async(queue='milho.plantar', serializer='json')
	plantarTrigo.apply_async(queue='trigo.plantar', serializer='json')

# for idx, item in enumerate(items):
