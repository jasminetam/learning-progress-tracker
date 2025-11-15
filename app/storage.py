from typing import Dict

from .schemas import Resource, StudySession

RESOURCES: Dict[int, Resource] = {}
SESSIONS: Dict[int, StudySession] = {}

resource_id_counter: int = 0
session_id_counter: int = 0


def next_resource_id() -> int:
    global resource_id_counter
    resource_id_counter += 1
    return resource_id_counter


def next_session_id() -> int:
    global session_id_counter
    session_id_counter += 1
    return session_id_counter
