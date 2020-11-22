"""Load the config settings."""
import json
import pathlib


_config_file = pathlib.Path(__file__).parent.absolute() / 'config.json'
with open(_config_file) as f:
    config = json.load(f)


ELO_K_FACTOR = config.get('elo_k_factor', 32)
TIMER_CHECK_INTERVAL = config.get('timer_check_interval', 60)    # seconds
MAX_SESSION_AGE = config.get('max_session_age', 30)    # days
HASHING_ALGORITHM = config.get('hashing_algorithm', 'sha256')

DB_NAME = config['db_name']
DB_USER = config.get('db_user', DB_NAME)
DB_PASSWORD = config.get('db_password', '')

SMTP_SERVER = config['smtp_server']
SMTP_PORT = config.get('smtp_port', 465)
SMTP_USERNAME = config['smtp_username']
SMTP_PASSWORD = config['smtp_password']
EMAIL_ADDRESS = config['email_address']
