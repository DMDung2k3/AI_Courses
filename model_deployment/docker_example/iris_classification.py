from sklearn import datasets
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import pickle

dataset = datasets.load_iris()
x = dataset.data
y = dataset.target

x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=0)

model = RandomForestClassifier()
model.fit(x_train, y_train)

data = {"features": [1,2,3,4]}
prediction = model.predict([data["features"]])[0]
print(prediction)
# y_pred = model.predict(x_test)

# print("Accuracy: %.2f" % accuracy_score(y_test, y_pred))

# with open("model.pkl", "wb") as f:
#     pickle.dump(model, f)