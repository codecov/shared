class EntityRateLimitedException(Exception):
    def __init__(self):
        self.message = "Entity is rate limited, please try again later"
