import json

object ={
    "class": None,
    "headers": 300
    }

object["name"] = "John";

print(object);

json = json.dumps(object, indent=4);

print(json)

print(eval('object' + '["name"]'))