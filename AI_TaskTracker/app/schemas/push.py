from pydantic import BaseModel


class PushSubscriptionIn(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


class PushSendIn(BaseModel):
    title: str
    body: str
    url: str = "/"
