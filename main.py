# # # # # # # # # # #
# Евстегней  Чачлык #
#      2020         #
# # # # # # # # # # #

import datetime
import json
import random
import time
from threading import Thread

import vk_api
from requests.exceptions import ReadTimeout
from vk_api.longpoll import VkLongPoll, VkEventType


class Config:
    __slots__ = ["Token", "Trigger",
                 "filename", "_data"]

    def __init__(self, filename):
        self.filename = filename
        self._data = None

    def load(self, ):
        with open(self.filename, "r", encoding="utf-8") as file:
            self._data = json.load(file)
            for (k, v) in self._data.items():
                setattr(self, k, v)

    def save(self):
        if self._data is not None:
            with open(self.filename, "w", encoding="utf-8") as file:
                json.dump(self._data, file, ensure_ascii=False, indent=4)

    def update(self):
        for k in self.__slots__[:-2]:
            self._data[k] = getattr(self, k)


class Message:
    def __init__(self, _user_id, _peer_id, _text, _message_id):
        self.user_id = _user_id
        self.peer_id = _peer_id
        self.name = GetNameUsers(self.user_id) + ":"
        self.text = _text
        self.message_id = _message_id
        self.date = datetime.datetime.now()
        self.deleted = False
        self.edited = False

    def set_deleted(self):
        self.deleted = True

    def get_deleted(self):
        return "[deleted]" if self.deleted else ""

    def set_edited(self):
        self.edited = True

    def get_edited(self):
        return "[edited]\n" if self.edited else " "


cfg = Config("config.json")
cfg.load()

vk_session = vk_api.VkApi(token=cfg.Token)
longpoll = VkLongPoll(vk_session)
vk = vk_session.get_api()

user_info = vk.users.get()[0]
user_id = user_info["id"]
user_name = f"{user_info['first_name']} {user_info['last_name']}"
print(f"{user_name},", end=" ")


def MessagesSend(_peer_id, _text, disable_mentions=1):
    return vk.messages.send(peer_id=_peer_id,
                            message=_text,
                            random_id=random.randint(-1000000, 1000000),
                            disable_mentions=disable_mentions)


def MessageDelete(mid, delete_for_all=1):
    vk.messages.delete(message_ids=mid,
                       delete_for_all=delete_for_all)


def GetNameUsers(user_ids):
    names = []
    resp = vk.users.get(user_ids=user_ids)
    for u in resp:
        names.append(f"@id{u['id']}({u['first_name']})")
    return ", ".join(names)


def run(target, arg=None, timeout=None):
    if arg is None:
        arg = []
    Thread(target=void, args=[target, arg, timeout], daemon=True).start()


def void(target, arg=None, timeout=None):
    if timeout is not None:
        time.sleep(timeout)
    if arg is None:
        arg = []
    target(*arg)


def clear_db():
    while True:
        _arr = db.copy()
        for i, item in _arr.items():
            if len(item) > 20:
                db[i] = db[i][len(item) - 20:]
        time.sleep(1200)


db = {}

run(clear_db, timeout=600)
print("Бот запущен")
while True:
    try:
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW:
                if event.from_chat and event.user_id > 0:
                    if event.user_id != user_id:
                        add_text = ""
                        if event.peer_id not in db:
                            db[event.peer_id] = []
                        if event.text:
                            add_text = event.text
                        else:
                            response = vk.messages.getById(message_ids=event.message_id)["items"]
                            if response:
                                response = response[0]
                                attach = response.get("attachments")
                                if attach:
                                    attach = attach[0].get("sticker")
                                    if attach is not None:
                                        add_text = attach["images"][len(attach["images"]) - 1]["url"]
                                    else:
                                        add_text = "[Вложение]"
                        db[event.peer_id].append(Message(event.user_id, event.peer_id, add_text, event.message_id))
                    else:
                        if not event.text:
                            continue
                        message = event.message.lower()

                        if message.startswith(cfg.Trigger):
                            cmd = message[len(cfg.Trigger):].strip()
                            show_only_deleted = cmd == "+"
                            response = vk.messages.getById(message_ids=event.message_id)["items"]
                            get_user_id = None
                            if response:
                                response = response[0]
                                reply_message = response.get("reply_message")
                                fwd_messages = response.get("fwd_messages")
                                if reply_message:
                                    get_user_id = reply_message["from_id"]
                                elif fwd_messages:
                                    get_user_id = fwd_messages[0]["from_id"]
                                else:
                                    get_user_id = None

                            text = f"Лог {GetNameUsers(get_user_id) if get_user_id else ''}:\n"
                            arr = db.get(event.peer_id, [])
                            for user in arr[len(arr) - (15 if get_user_id else 10):]:
                                if user.user_id == get_user_id or not get_user_id:
                                    if (show_only_deleted and user.deleted) or not show_only_deleted:
                                        text += f"{user.name if not get_user_id else '--'} {user.get_edited()}" \
                                                f"{user.get_deleted()} {user.text}" \
                                                f"\n"
                            MessagesSend(event.peer_id, text)
                            MessageDelete(event.message_id)

            if event.type == VkEventType.MESSAGE_FLAGS_SET and event.raw[0] == 2:
                if event.peer_id in db:
                    for user in db.get(event.peer_id, []):
                        if user.message_id == event.message_id:
                            user.set_deleted()

            if event.type == VkEventType.MESSAGE_EDIT and event.raw[0] == 5:
                if event.peer_id in db:
                    for user in db.get(event.peer_id, []):
                        if user.message_id == event.message_id:
                            user.text += f"\n↓\n{event.text}"
                            user.edited = True

    except ReadTimeout:
        pass

    except Exception as e:
        print("Основной поток: ", e)
        time.sleep(10)

# Messages.select().where(Messages.peer_id == event.peer_id).order_by(Messages.id.desc()).limit(10)
