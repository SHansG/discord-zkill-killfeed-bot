def create_db(client, name) -> None:
    db = client[name]
    settings_collection = db["Settings"]
    # populate collection with initial document
    settings_collection.insert_one({"_id":0})