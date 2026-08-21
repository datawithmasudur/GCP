import json
import time
import random
from google.cloud import pubsub_v1

project_id = "upbeat-math-480123-r1"
topic_id = "sales-events"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_id)

products = ["Laptop", "Mouse", "Keyboard", "Monitor"]

while True:
    event = {
        "product": random.choice(products),
        "sales": round(random.uniform(10, 1000), 2)
    }
    data = json.dumps(event).encode("utf-8")
    publisher.publish(topic_path, data)
    print(f"Published: {event}")
    time.sleep(3)
