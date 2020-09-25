import datetime as dt

import sqlalchemy as sql
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Event(Base):
    sqlite_autoincrement=True
    __tablename__ = "eventtable"
    id = sql.Column(sql.Integer, primary_key=True)
    name = sql.Column(sql.Unicode)
    primary_photo_id = sql.Column(sql.Integer)
    time_created = sql.Column(sql.Integer)
    primary_source_id = sql.Column(sql.String)
    comment = sql.Column(sql.String)

    def __init__(self, name, primary_photo_id):
        self.name = name
        self.primary_photo_id = primary_photo_id
        self.time_created = dt.datetime.now().timestamp()

    def __str__(self):
        return "<Event id=%s name=%s>" % (self.id, self.name)


class Photo(Base):
    __tablename__ = "phototable"
    id = sql.Column(sql.Integer, primary_key=True)
    event_id = sql.Column(sql.Integer, sql.schema.ForeignKey(Event.id))
    event = sql.orm.relationship(Event, backref=sql.orm.backref('photos'))
    filename = sql.Column(sql.Unicode)


class Video(Base):
    __tablename__ = "videotable"
    id = sql.Column(sql.Integer, primary_key=True)
    event_id = sql.Column(sql.Integer, sql.schema.ForeignKey(Event.id))
    event = sql.orm.relationship(Event, backref=sql.orm.backref('videos'))
    filename = sql.Column(sql.Unicode)


class Issue:
    def __init__(self, folder, event, files):
        self.folder = folder
        self.event = event
        self.files = files
        self.action = None

    def solved(self):
        return self.action is False

    def solve(self):
        if self.action:
            self.action()

    def move_files(self):
        pass

    def change_event(self):
        pass

    def change_both(self):
        pass


class DataIter:
    def __init__(self, data):
        self._data = data
        self._currentIndex = 0

    def __next__(self):
        if self._currentIndex >= len(self._data)-1:
            raise StopIteration
        return self.next()

    def __int__(self):
        return self._currentIndex

    def key(self):
        return list(self._data.keys())[self._currentIndex]

    def this(self):
        return self._data[self.key()]

    def next(self):
        self._currentIndex += 1
        self._currentIndex %= len(self._data)
        return self.this()

    def prev(self):
        self._currentIndex -= 1
        self._currentIndex %= len(self._data)
        return self.this()


class Data(dict):
    def __iter__(self):
        return DataIter(self)