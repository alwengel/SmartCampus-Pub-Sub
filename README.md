# SmartCampus-Pub-Sub
SmartCampus dataset has been expanded with subscriptions to be used for evaluating Pub-Sub systems. Subscriptions are found in SQL and natural language.


## Instructions

Use **db_handler.py** to interact with the database. To get a random selection of publications use method **get_random_publications_with_matches**. This saves a number of random publications along with their matching subscriptions as a json. Use variable **number_of_publications** to control how many publications are saved. To save subscriptions as json use method **get_subscriptions()**. It takes argument **version** which can either be _sql_ or _nlp_.
