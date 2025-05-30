# SmartCampus-Pub-Sub
SmartCampus dataset has been expanded with subscriptions to be used for evaluating Pub-Sub systems. Subscriptions are found in SQL and natural language. When handling the database, keep in mind that there are millions of rows so some actions might take a while or demand that you handle the db in batches so that your machine doesn't run out of memory.

## **Database Schema**
The only not-straight-forward data type is `subscription_matches` in Table `publications` which is a **BLOB**. In this case it is an 8-byte BLOB which represents a 64-bit bitmask. In `db_handler.py` there is a method, `decode_blob_to_integers()` that decodes a blob into a list of integers where each integer corresponds with _a matching `subscription_id` for that publication_.

### **Table: `subscriptions`**
| Column                   | Type     |
|--------------------------|----------|
| `id`                     | INTEGER  |
| `complexity`             | TEXT     |
| `nlp_subscription`       | TEXT     |
| `publication_match_count`| INTEGER  |
| `sql_subscription`       | TEXT     |

### **Table: `publications`**
| Column               | Type     |
|----------------------|----------|
| `id`                 | INTEGER PRIMARY KEY AUTOINCREMENT |
| `publication_id`     | -        |
| `timestamp`          | -        |
| `deveui`             | -        |
| `temperature`        | -        |
| `humidity`           | -        |
| `light`              | -        |
| `motion`             | -        |
| `co2`                | -        |
| `battery`            | -        |
| `sound_avg`          | -        |
| `sound_peak`         | -        |
| `moisture`           | -        |
| `pressure`           | -        |
| `acceleration_x`     | -        |
| `acceleration_y`     | -        |
| `acceleration_z`     | -        |
| `rssi`               | -        |
| `lsnr`               | -        |
| `chan`               | -        |
| `port`               | -        |
| `rfch`               | -        |
| `seqn`               | -        |
| `fcnt`               | -        |
| `sensor_type`        | -        |
| `floor`              | -        |
| `location`           | -        |
| `publication`        | -        |
| `subscription_matches`| BLOB    |
| `timestamp_unix`     | -        |

## Instructions

Use **db_handler.py** to interact with the database. To get a random selection of publications use method **get_random_publications_with_matches**. This saves a number of random publications along with their matching subscriptions as a json. Use variable **number_of_publications** to control how many publications are saved. Format of saved publications:

```
[
  {
    "publication_id": <id>,
    "publication": <publication>,
    "subscription_matches": [
      {
        "subscription_id": <id>,
        "subscription": <subscription>
      },
      // more subscriptions matching the publication
    ]
  },
  // more publications
]
```

To save subscriptions as json use method **get_subscriptions()**. It takes argument **version** which can either be _sql_ or _nlp_. Format of saved subscriptions:
```
[
  {
    "subscription_id": <id>,
    "subscriptions": <subscription>
  },
  // other subscriptions
]
```
- See file **schema.sql** to understand the schema of cardiffnlp.db


## Download DB
Download smartcampus.db from [here](https://helsinkifi-my.sharepoint.com/:u:/g/personal/alwengel_ad_helsinki_fi/EYkPmao844JMk1MMxATrQg8BmYmxTn_cBSjXSN8iIcjdDA?e=Rw4FUq).

## Original SmartCampus README
Find it [here](ORIGINAL_SMARTCAMPUS_README.md).