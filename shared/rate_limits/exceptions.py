class EntityRateLimitedException(Exception):
    def __init__(self, entity_name: str):
        self.message = "Entity is rate limited, please try again later"
        self.entity_name = entity_name
