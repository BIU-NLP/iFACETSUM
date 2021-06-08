from datetime import datetime

# the web server port:
http_server_port = 5432 # 1399

# should the web server be over https or http
# when this server is used in the nlp servers, where planet is the client, even
# when https is needed (like for MTurk), the server can be started as http.
# notice that there should be a folder named 'ssl' in this directory with the files
# cert.pem and key.pem.
is_https = False
https_certificate_file = 'ssl/cert.pem'
https_key_file = 'ssl/key.pem'

time_to_sleep_between_background_save = 60

table_results_path = 'data/db/table_results_{}.json'.format(datetime.now().strftime("%Y%m%d%H%M%S"))
csv_delimiter = ','
csv_text_quotechar = '"'