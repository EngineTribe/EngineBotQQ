from pydantic import BaseModel
from enum import Enum
from typing import Optional


class ServerStats(BaseModel):
    os: str
    python: str
    player_count: int
    level_count: int
    uptime: int
    connection_per_minute: int


class CQHTTPEventType(str, Enum):
    message = "message"
    notice = "notice"


class CQHTTPNoticeType(str, Enum):
    group_upload = "group_upload"
    group_admin = "group_admin"
    group_decrease = "group_decrease"
    group_increase = "group_increase"
    group_ban = "group_ban"
    friend_add = "friend_add"
    group_recall = "group_recall"
    friend_recall = "friend_recall"
    group_card = "group_card"
    offline_file = "offline_file"
    client_status = "client_status"
    essence = "essence"
    notify = "notify"


class CQHTTPMessageType(str, Enum):
    friend = "friend"
    group = "group"


class CQHTTPMessageSenderRole(str, Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class CQHTTPMessageSender(BaseModel):
    user_id: int
    nickname: str
    sex: str
    age: int
    group_id: Optional[int] = None
    card: Optional[str] = None
    area: Optional[str] = None
    level: Optional[str] = None
    role: CQHTTPMessageSenderRole
    title: Optional[str] = None


class CQHTTPRequest(BaseModel):
    time: int
    self_id: int
    post_type: CQHTTPEventType

    notice_type: Optional[CQHTTPNoticeType] = None

    message_type: Optional[CQHTTPMessageType] = None
    sub_type: Optional[str] = None
    message_id: Optional[int] = None
    message_seq: Optional[int] = None
    user_id: Optional[int] = None
    sender: Optional[CQHTTPMessageSender] = None
    message: Optional[str] = None
    raw_message: Optional[str] = None
    font: Optional[int] = None

    group_id: Optional[int] = None

    temp_source: Optional[int] = None
    anonymous: Optional[dict] = None


class CQHTTPQuickReply(BaseModel):
    reply: str
    auto_escape: bool = False
    delete: bool = False
    at_sender: bool = False


class RegisterCodeOperation(str, Enum):
    register = "r"
    change_password = "c"


class RegisterCode(BaseModel):
    operation: RegisterCodeOperation
    username: str
    password_hash: str
