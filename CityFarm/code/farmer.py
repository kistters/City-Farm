from tasks import plant

#plant.apply_async(("corn",), queue='planting', serializer='json')
#plant.apply_async(("wheat",), queue='planting', serializer='json')
plant.apply_async(["corn"], queue='planting', serializer='json')
plant.apply_async(["wheat"], queue='planting', serializer='json')

# for idx, item in enumerate(items):
