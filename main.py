# # # # # # # # # # #
# Евстегней  Чачлык #
#      2020         #
# # # # # # # # # # #
import codecs
import datetime
import json
import random
import shutil
import time
from os.path import isfile
from threading import Thread

import vk_api
from requests.exceptions import ReadTimeout
from vk_api.longpoll import VkLongPoll, VkEventType


class Config:
    __slots__ = ["Token", "Trigger", "WhiteListChat", "TriggerToAddChat", "TriggerShowChats",
                 "filename", "_data"]

    def __init__(self, filename):
        self.filename = filename
        self._data = None

    def load(self, ):
        with codecs.open(self.filename, "r", "utf-8-sig") as file:
            self._data = json.load(file)
            for (k, v) in self._data.items():
                setattr(self, k, v)

    def save(self):
        if self._data is not None:
            with codecs.open(self.filename, "w", "utf-8-sig") as file:
                json.dump(self._data, file, ensure_ascii=False, indent=4)

    def update(self):
        for k in self.__slots__[:-2]:
            self._data[k] = getattr(self, k, "")

    def check(self):
        if not isfile('config.json'):
            try:
                shutil.copy('config.json.sample', 'config.json')
                exit("Настрой файл config.json")
            except Exception as s:
                exit("Проверьте ваши права на данную папку!")
                # Чтобы линт не ругался
                print(s)
        else:
            self.load()
            for x in self.__slots__[:-2]:
                try:
                    if getattr(self, x) == "":
                        raise ValueError
                except AttributeError:
                    self.update()
                    self.save()
                    exit("У тебя неправильно настроен конфиг. Перезапусти скрипт и настрой config.json")
                except Exception as s:
                    exit("Заполни все пустые строки в config.json")
                    # Чтобы линт не ругался
                    print(s)


class Message:
    def __init__(self, _user_id, _peer_id, _message_id):
        self.user_id = _user_id
        self.peer_id = _peer_id
        self.access = self.peer_id in cfg.WhiteListChat
        self.name = GetNameUsers(self.user_id) + ":"
        self._text = ""
        self.attachments = []
        self.message_id = _message_id
        self.date = datetime.datetime.now()
        self.deleted = False
        self.edited = False
        self.count_edited = 0
        self.audio = False

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value

    @text.getter
    def text(self):
        if self.access:
            return self._text
        else:
            if self._text:
                return self._text
            else:
                return "[Вложение]"

    def set_deleted(self):
        self.deleted = True

    def get_deleted(self):
        return "[deleted]" if self.deleted else ""

    def set_edited(self):
        self.edited = True

    def get_edited(self):
        return "[edited]\n" if self.edited else " "

    def set_audio(self):
        self.audio = True

    def __repr__(self):
        return f"{self.user_id}:{self.peer_id}:{self.message_id}"


cfg = Config("config.json")
cfg.check()

vk_session = vk_api.VkApi(token=cfg.Token)
longpoll = VkLongPoll(vk_session)
vk = vk_session.get_api()

user_info = vk.users.get()[0]
user_id = user_info["id"]
user_name = f"{user_info['first_name']} {user_info['last_name']}"
print(f"{user_name},", end=" ")


def MessagesSend(_peer_id, _text, disable_mentions=1):
    return vk.messages.send(peer_id=_peer_id,
                            message=ReplaceBennedWord(_text.replace('&lt;', '<')
                                                      .replace('&gt;', '>')
                                                      .replace('&quot;', '"')
                                                      .replace('&amp;', '&')),
                            random_id=random.randint(-1000000, 1000000),
                            disable_mentions=disable_mentions,
                            dont_parse_links=1)


def MessageDelete(mid, delete_for_all=1):
    vk.messages.delete(message_ids=mid,
                       delete_for_all=delete_for_all)


def GetAllAttachments(msg: Message):
    response = vk.messages.getById(message_ids=msg.message_id)["items"]
    if response:
        response = response[0]
        attachments = response.get("attachments")
        _arr = []
        if not msg.attachments:
            msg.attachments = []
        for attach in attachments:
            audio_message = attach.get("audio_message")
            if audio_message:
                msg.attachments.append(audio_message.get("link_ogg"))
                msg.set_audio()
                break

            sticker = attach.get("sticker")
            if sticker:
                msg.attachments.append(sticker["images"][len(sticker["images"]) - 1]["url"])

            photo = attach.get("photo")
            if photo:
                msg.attachments.append(photo["sizes"][len(photo["sizes"]) - 1]["url"])

            video = attach.get("video")
            if video:
                msg.attachments.append(f"https://vk.com/video{video['owner_id']}_{video['id']}")
    return msg


def GetNameUsers(user_ids):
    names = []
    resp = vk.users.get(user_ids=user_ids)
    for u in resp:
        names.append(f"@id{u['id']}({u['first_name']})")
    return ", ".join(names)


def MessageEdit(mid, t, peer):
    vk.messages.edit(peer_id=peer,
                     message_id=mid,
                     message=t)


def run(target, arg=None, timeout=None):
    if arg is None:
        arg = []
    Thread(target=void, args=[target, arg, timeout], daemon=True).start()


def void(target, arg=None, timeout=None):
    if timeout is not None:
        time.sleep(timeout)
    if arg is None:
        arg = []
    try:
        target(*arg)
    except Exception as s:
        print(f"Ошибка в функции {target.__name__}\n"
              f"Аргументы: {arg}\n"
              f"Ошибка: {s}\n"
              f"Отправьте разработчику!")


def clear_db():
    while True:
        _arr = db.copy()
        for i, item in _arr.items():
            if len(item) > 20:
                db[i] = db[i][len(item) - 20:]
        time.sleep(1200)


def ReplaceBennedWord(text):
    for c, v in banned_word.items():
        text = text.replace(c, v)
    return text


db = {}
banned_word = {
    "vto.pe": "впо.пе",
    "@all": "<all>",
    "@everyone": "<all>",
    "@тут": "<онлине>",
    "@все": "<алл>",
    "@здесь": "<онлине>",
    "@here": "<онлине>",
    "@online": "<онлине>"
}


# run(clear_db, timeout=600)
def main():
    print("Бот запущен")
    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW:
                    if event.from_chat and event.user_id > 0:
                        if event.user_id != user_id:
                            msg = Message(event.user_id, event.peer_id, event.message_id)
                            if event.peer_id not in db:
                                db[event.peer_id] = []
                            if event.text:
                                msg.text = event.text[:150]
                            else:
                                if msg.access:
                                    msg = GetAllAttachments(msg)
                            _len = len(db[event.peer_id])
                            if _len > 500:
                                db[event.peer_id] = db[event.peer_id][_len - 250:]
                            db[event.peer_id].append(msg)
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

                                text = f"Лог {GetNameUsers(get_user_id) if get_user_id else ''}:\n"
                                arr = db.get(event.peer_id, [])
                                logs = []
                                for user in arr:
                                    if user.user_id == get_user_id or not get_user_id:
                                        if (show_only_deleted and user.deleted) or not show_only_deleted:
                                            logs.append(user)
                                lastUser = 0
                                logs = logs if len(logs) < 10 else logs[len(logs) - 10:]
                                for user in logs:
                                    a = "Все вложения:\n " + "\n".join(list(set(user.attachments))) + "\n"
                                    if get_user_id or (lastUser == user.user_id):
                                        name = "--"
                                    else:
                                        name = user.name
                                    lastUser = user.user_id
                                    text += f"{name} {user.get_edited()}" \
                                            f"{user.get_deleted()} {user.text}\n" \
                                            f"{a if user.attachments else ''}" \
                                            f"{'' if get_user_id else ''}"
                                MessagesSend(event.peer_id, text)
                                MessageDelete(event.message_id)

                            if message == cfg.TriggerToAddChat:
                                if event.peer_id in cfg.WhiteListChat:
                                    cfg.WhiteListChat.remove(event.peer_id)
                                    MessageEdit(event.message_id, f"Беседа <<{event.peer_id}>> удалена.", event.peer_id)
                                else:
                                    cfg.WhiteListChat.append(event.peer_id)
                                    MessageEdit(event.message_id, f"Беседа <<{event.peer_id}>> добавлена.",
                                                event.peer_id)
                                run(target=MessageDelete, arg=[event.message_id], timeout=5)
                                cfg.update()
                                cfg.save()

                            if message == cfg.TriggerShowChats:
                                chats = "\n".join(
                                    list(map(lambda x: f"{x} {'✅' if event.peer_id == x else ''}", cfg.WhiteListChat)))
                                MessageEdit(event.message_id,
                                            f"Все чаты в которых включено получение вложений:\n {chats}", event.peer_id)
                                run(target=MessageDelete, arg=[event.message_id], timeout=10)

                if event.type == VkEventType.MESSAGE_FLAGS_SET and event.raw[0] == 2:
                    if event.peer_id in db:
                        for user in db.get(event.peer_id, []):
                            if user.message_id == event.message_id:
                                user.set_deleted()

                if event.type == VkEventType.MESSAGE_EDIT and event.raw[0] == 5:
                    if event.peer_id in db:
                        for user in db.get(event.peer_id, []):
                            if user.message_id == event.message_id and not user.audio and user.count_edited <= 4:
                                if user.access:
                                    user = GetAllAttachments(user)
                                user.text += f"\n↓\n{event.text[:100]}"
                                user.edited = True
                                user.count_edited += 1
                            if user.count_edited == 5:
                                user.text += f"\n[Редактирований > 5]"

        except ReadTimeout:
            pass

        except Exception as e:
            print("Основной поток: ", e)
            time.sleep(10)


if __name__ == '__main__':
    main()
