from datetime import datetime
import configparser

import gspread
import pandas as pd
from gspread_dataframe import get_as_dataframe
from oauth2client.service_account import ServiceAccountCredentials
from telethon import TelegramClient
from telethon.tl.functions.messages import CreateChatRequest, EditChatAdminRequest, \
    GetAllChatsRequest, ToggleChatAdminsRequest, DeleteChatUserRequest

from src.employee import *


def get_table(config):

    credentials = ServiceAccountCredentials.from_json_keyfile_name(config["PATH_TO_JSON_KEYFILE"],
                                                                   config["SCOPE"])
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(config["DOC_ID"])

    table = get_as_dataframe(spreadsheet.worksheets()[0],
                             parse_dates=True,
                             usecols=[0, 1, 2, 4],
                             skiprows=1,
                             names="name,username,birthday,sex".split(','))

    table = table.dropna().reset_index(drop=True)
    table["birthday"] = table["birthday"].apply(lambda x: pd.to_datetime(x, format="%m/%d"))

    return table


def birthday_is_soon(employees):

    now = datetime.now()

    birthday_guys = []

    for employee in employees:
        employee.birthday = employee.birthday.replace(year=now.year)

        if now > employee.birthday:
            employee.birthday = employee.birthday.replace(year=now.year + 1)

        if (employee.birthday - now).days <= 14:
            birthday_guys.append(employee)

    return birthday_guys


def setting_telegram_connection(config):
    client = TelegramClient(config["SessionID"], int(config["ApiID"]), config["ApiHash"])
    if client.connect():
        if not client.is_user_authorized():
            print("Oh, I still hadn't signed you in. Let's fix this.")
            client.send_code_request(config["PhoneNumber"])
            client.sign_in(config["PhoneNumber"], input("Enter code from your mobile app: "))
        return client
    else:
        print("Fail to connect")
        return None


def create_birthday_chat(client, config, birthday_guy, responsible_guy, employees):

    congratulators_usernames = []
    for employee in employees:
        if employee.username != birthday_guy.username:
                congratulators_usernames.append(employee.username)

    updates = client(CreateChatRequest(users=congratulators_usernames,
                                       title=config["TITLE_TEMPLATE"].format(name=birthday_guy.name,
                                                                             day=birthday_guy.birthday.day,
                                                                             month=birthday_guy.birthday.month,
                                                                             year=birthday_guy.birthday.year)))

    birthday_chat = updates.chats[0]

    # Setting responsible_guy as admin
    client(ToggleChatAdminsRequest(chat_id=birthday_chat.id, enabled=True))
    client(EditChatAdminRequest(chat_id=birthday_chat.id,
                                user_id=responsible_guy.username,
                                is_admin=1))

    # Sending greeting message
    client.send_message(birthday_chat,
                        config["GREETING_MESSAGE"].format(name=birthday_guy.name,
                                                          responsible_guy_name=responsible_guy.name,
                                                          responsible_guy_username=responsible_guy.username))

    # Deleting myself in case its my birthday
    if birthday_guy.username == config["MyUsername"]:
        client(DeleteChatUserRequest(chat_id=birthday_chat.id,
                                     user_id=config["MyUsername"]))

    return 0


def get_responsible_guy(birthday_guy, employees):
    responsible_guy = employees[0]
    return responsible_guy


def chat_exists(config, client, birthday_guy):
    for chat in client(GetAllChatsRequest(except_ids=[])).chats:
        if chat.title == config["TITLE_TEMPLATE"].format(name=birthday_guy.name,
                                                         day=birthday_guy.birthday.day,
                                                         month=birthday_guy.birthday.month,
                                                         year=birthday_guy.birthday.year) and \
                not chat.deactivated:
            return 1
    return 0


def main():

    config = configparser.ConfigParser()
    config.read("../data/config.ini")
    telegram_config = config["telegram"]

    client = setting_telegram_connection(telegram_config)

    data = get_table(config)

    employees = []

    for index, row in data.iterrows():
        new_employee = Employee(base_id=index,
                                telegram_username=row['username'],
                                name=' '.join(row['name'].split()[::-1]),
                                birthday=row['birthday'])
        employees.append(new_employee)

    birthday_guys = birthday_is_soon(employees)
    for birthday_guy in birthday_guys:
        if not chat_exists(config, client, birthday_guy):
            responsible_guy = get_responsible_guy(birthday_guy, employees)
            create_birthday_chat(client, telegram_config, birthday_guy, responsible_guy, employees)


if __name__ == "__main__":
    main()
