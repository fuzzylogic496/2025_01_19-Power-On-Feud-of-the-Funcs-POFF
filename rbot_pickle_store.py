# rbot_pickle_store.py
import os
import pickle
import tempfile

DEFAULT_PICKLE = "rbot_memory.pkl"

def save_memory_pickle(memory, path=DEFAULT_PICKLE):
    dirn = os.path.dirname(path) or "."
    fd, tmppath = tempfile.mkstemp(dir=dirn)
    try:
        with os.fdopen(fd, "wb") as f:
            pickle.dump(memory, f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmppath, path)
    finally:
        if os.path.exists(tmppath):
            try:
                os.remove(tmppath)
            except Exception:
                pass

def load_memory_pickle(path=DEFAULT_PICKLE):
    if not os.path.exists(path):
        return {}
    with open(path, "rb") as f:
        return pickle.load(f)
