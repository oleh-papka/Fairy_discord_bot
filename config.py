import os
import logging
import time

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%d-%b %H:%M:%S', level=logging.INFO
)

logger = logging.getLogger(__name__)

BOT_VERSION = ''
BOT_PREFIX = ''
BOT_STARTED_AT = time.time()
OWNER_NAME = ''

BOT_TOKEN = os.environ.get('BOT_TOKEN')
OWNER_ID = os.environ.get('OWNER_ID')
