from fastapi import FastAPI
import pickle
with open("model.pkl", "rb") as f:
    model = pickle.load(f)

class_names = ["Iris-Setosa", "Iris-Versicolour", "Iris-Virginica"]

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "ML deployment model"}

@app.post("/predict")
def predict(data:dict):
    prediction = model.predict([data["features"]])[0]
    predicted_class = class_names[prediction]
    return {"message": predicted_class}