class Employee:

    def __init__(self, base_id, telegram_username, name, birthday):
        self.id = base_id
        self.username = telegram_username
        self.name = name
        self.birthday = birthday
        self.connections = []

    def add_connection(self, colleague):
        self.connections.append(colleague)


class Team:

    def __init__(self, teammates):
        self.teammates = teammates
