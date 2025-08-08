from dataclasses import asdict, is_dataclass
import json
import os
import hashlib
import time

def to_hash(data):
    return hashlib.sha256(str(data).encode()).hexdigest()

def proof_of_work(data, interactions, prefix='0000', progress_callback=None) -> dict:
    nonce = 0
    start = time.time()
    nonces = []
    for _ in range(interactions):
        while True:
            attempt = f"{data}|{nonce}"
            hash_result = to_hash(attempt)
            if hash_result.startswith(prefix):
                nonces.append(nonce)
                if progress_callback:
                    progress_callback(data, nonces)
                nonce += 1
                break
            nonce += 1

    end = time.time()
    return {
        'data': data,
        'nonces': nonces,
        'time_spent': round(end - start, 2)
    }

def verify_proof_of_work(data, nonces, prefix='0000'):
    for nonce in nonces:
        attempt = f"{data}|{nonce}"
        hash_result = to_hash(attempt)
        if not hash_result.startswith(prefix):
            return False
    return True
    
def serialize(obj):
    if is_dataclass(obj):
        return asdict(obj)
    raise TypeError(f"Type {type(obj)} not serializable")
    
def write_json(contents, folder, filename):    
    folder = f'data/{folder}'
    full_path = os.path.join(folder, filename)
    
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    with open(full_path, 'w') as file:
        json.dump(contents, file, indent=4, default=serialize)
    
    return full_path
    
def load_json(full_path):
    with open(full_path, 'r') as file:
        return json.load(file)  
