from tasks import eat

eat.apply_async(("corn",), queue='eating', serializer='json')
eat.apply_async(("wheat",), queue='eating', serializer='json')
