import os

COREF_TYPE_PROPOSITIONS = "propositions"
COREF_TYPE_EVENTS = "events"
COREF_TYPE_ENTITIES = "entities"

MAX_MENTIONS_IN_CLUSTER = 50

IS_DEBUG_MODE = os.getenv("DEBUG_MODE") == "true"