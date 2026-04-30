import placeholder_lidarSDK
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DUMMY_DISTANCE = 3.5 # meters

def get_distance():
    logger.info("distance: %.2fm", DUMMY_DISTANCE)
    return {"distance": DUMMY_DISTANCE}
