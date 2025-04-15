CREATE TABLE publications (publication_id , timestamp , deveui , temperature , humidity , light , motion , co2 , battery , sound_avg , sound_peak , moisture , pressure , acceleration_x , acceleration_y , acceleration_z , rssi , lsnr , chan , port , rfch , seqn , fcnt , sensor_type , floor , location , publication , subscription_matches , timestamp_unix );

CREATE TABLE subscriptions (id INTEGER, complexity TEXT, nlp_subscription TEXT, publication_match_count INTEGER, sql_subscription TEXT);

