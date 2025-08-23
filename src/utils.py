from dataclasses import asdict, is_dataclass
import json
import os
import hashlib
import time
import glob
from typing import Any, Callable, Dict, List, Optional, Union

DEFAULT_PREFIX = '0'


def to_hash(data: Any) -> str:
    """
    Generate a SHA-256 hash for the given data.
    """
    return hashlib.sha256(str(data).encode()).hexdigest()

def proof_of_work(
    data: Any,
    interactions: int,
    prefix: str = DEFAULT_PREFIX,
    progress_callback: Optional[Callable[[Any, List[int]], None]] = None
) -> Dict[str, Any]:
    """
    Perform a proof-of-work algorithm for a given number of interactions.
    Returns a dict with the data, list of nonces, and time spent.
    """
    nonce = 0
    start = time.time()
    nonces: List[int] = []
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

def verify_proof_of_work(
    data: Any,
    nonces: List[int],
    prefix: str = DEFAULT_PREFIX
) -> bool:
    """
    Verify a proof-of-work by checking that each nonce produces a hash with the required prefix.
    """
    for nonce in nonces:
        attempt = f"{data}|{nonce}"
        hash_result = to_hash(attempt)
        if not hash_result.startswith(prefix):
            return False
    return True

def serialize(obj: Any) -> Dict[str, Any]:
    """
    Serialize a dataclass object to a dictionary.
    Raises TypeError if the object is not a dataclass.
    """
    if is_dataclass(obj):
        return asdict(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

def write_json(contents: Any, folder: str, filename: str) -> str:
    """
    Write contents as JSON to the specified folder and filename.
    Returns the full file path.
    """
    full_path = os.path.join(folder, filename)
    try:
        if not os.path.exists(folder):
            os.makedirs(folder)
        with open(full_path, 'w') as file:
            json.dump(contents, file, indent=4, default=serialize)
    except Exception as e:
        print(f"Error writing JSON to {full_path}: {e}")
        raise
    return full_path

def load_json(full_path: str) -> Any:
    """
    Load and return JSON data from the specified file path.
    """
    try:
        with open(full_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading JSON from {full_path}: {e}")
        raise

def get_files_path_by_patterns(patterns: List[str]) -> List[str]:
    """
    Return a list of file paths matching any of the given glob patterns.
    """
    results: List[str] = []
    for pattern in patterns:
        results.extend(glob.glob(pattern))
    return results
