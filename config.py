import yaml
import os

config_path = os.getenv('CONFIG_PATH', 'config.yml')
_config = yaml.safe_load(open(config_path, 'r'))

GO_CQHTTP_HOST = _config['go_cqhttp']['host']
GO_CQHTTP_PORT = _config['go_cqhttp']['port']
GO_CQHTTP_USER_ID = _config['go_cqhttp']['user_id']
GO_CQHTTP_STANDALONE = _config['go_cqhttp']['standalone']

BOT_ADMIN = _config['bot']['admin']
BOT_ENABLED_GROUPS = _config['bot']['enabled_groups']

API_HOST = _config['enginetribe_api']['host']
API_KEY = _config['enginetribe_api']['api_key']
API_TOKEN = _config['enginetribe_api']['token']

WEBHOOK_HOST = _config['webhook']['host']
WEBHOOK_PORT = _config['webhook']['port']