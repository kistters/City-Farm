import json
import os
import shutil
import hashlib
import time


def write_to_file(path, filename, contents):
    full_path = os.path.join(path, filename)
    if not os.path.exists(path):
        os.makedirs(path)
    
    
    with open(full_path, 'w') as file:
        if isinstance(contents, dict):
            json.dump(contents, file, indent=4)
        elif isinstance(contents, str):
            file.write(contents)
        else:
            raise TypeError("Contents must be either a string or a dictionary")


def move_file(file_path, target_directory):
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)

    shutil.move(file_path, target_directory)



def proof_of_work(data, required_days):
    nonce = 0
    prefix = '00000'
    start = time.time()
    nonces = []
    for _ in range(required_days):
        while True:
            attempt = f"{data}|{nonce}"
            hash_result = hashlib.sha256(attempt.encode()).hexdigest()
            if hash_result.startswith(prefix):
                nonces.append(nonce)
                print("find one more, ", nonces)
                nonce += 1
                break
            nonce += 1

    end = time.time()
    return {
        'data': data,
        'nonces': nonces,
        'time_spent': round(end - start, 2)
    }

def verify_pow(data, nonces, required_days):
    prefix = '00000'

    for nonce in nonces:
        attempt = f"{data}|{nonce}"
        hash_result = hashlib.sha256(attempt.encode()).hexdigest()
        if not hash_result.startswith(prefix):
            return False
    
    return required_days == len(nonces)



if __name__ == "__main__":
    result = proof_of_work('tomato', required_days=5)
    print(result, verify_pow('tomato', nonces=result.get('nonces'), required_days=5))
