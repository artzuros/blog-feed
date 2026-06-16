import atexit

from posthog import Posthog
from config.settings import POSTHOG_PROJECT_TOKEN, POSTHOG_HOST

posthog_client = Posthog(
    project_api_key=POSTHOG_PROJECT_TOKEN,
    host=POSTHOG_HOST,
    enable_exception_autocapture=True,
)

atexit.register(posthog_client.shutdown)
