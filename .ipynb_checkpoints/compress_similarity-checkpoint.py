import pickle
import gzip

with open("similarity.pkl", "rb") as f:
    similarity = pickle.load(f)

with gzip.open("similarity.pkl.gz", "wb") as f:
    pickle.dump(similarity, f)
