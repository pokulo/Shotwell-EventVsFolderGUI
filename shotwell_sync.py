#! /usr/bin/python3
import sqlalchemy as sql
from sqlalchemy.ext.declarative import declarative_base
import gi 
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf
import datetime as dt
import os

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


class ThumbnailButton(Gtk.CheckButton):
    def __init__(self, filename):
        super(ThumbnailButton, self).__init__()
        self.set_mode(draw_indicator=False)
        self._image = Gtk.Image()
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(filename, width=220, height=220,preserve_aspect_ratio=True)
        self._image.set_from_pixbuf(pixbuf)
        self.set_image(self._image)

    @property
    def selected(self):
        return self.get_active()

    @selected.setter
    def selected(self, active):
        self.set_active(active)


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


class ToggleButtonWindow(Gtk.Window):
    _EVENT = 1
    _PATH = 0

    def __init__(self, dbsession):
        self._data_iter = None
        self._data = Data()
        self.results = {}
        self.thumbnails = []
        self.dbsession = dbsession

        #GUI
        Gtk.Window.__init__(self, title="Shotwell folder  <-> event sync")
        self.set_border_width(10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        self.progressbar = Gtk.ProgressBar()
        vbox.pack_start(self.progressbar, False, True, 0)

        self.label = Gtk.Label()
        vbox.pack_start(self.label, False, True, 0)

        chooseBox = Gtk.Box(spacing=6)
        vbox.pack_start(chooseBox, False, True, 0)

        select_all_button = Gtk.Button("Alle Auswählen")
        select_all_button.connect("clicked", self.toggle_select_all_images)
        vbox.pack_start(select_all_button, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.thumbnailgrid = Gtk.FlowBox()
        self.thumbnailgrid.set_valign(Gtk.Align.START)
        self.thumbnailgrid.set_max_children_per_line(30)
        self.thumbnailgrid.set_selection_mode(Gtk.SelectionMode.NONE)

        scrolled.add(self.thumbnailgrid)
        vbox.pack_start(scrolled, True, True, 0)

        self.button = []
        self.button.insert(self._PATH, Gtk.ToggleButton("Pfad"))
        self.button[self._PATH].connect("toggled", self.chose, self._PATH)
        chooseBox.pack_start(self.button[self._PATH], True, True, 0)

        self.button.insert(self._EVENT, Gtk.ToggleButton("Event"))
        self.button[self._EVENT].connect("toggled", self.chose, self._EVENT)
        chooseBox.pack_start(self.button[self._EVENT], True, True, 0)

        CASBox = Gtk.Box(spacing=6)
        vbox.pack_start(CASBox, False, True, 0)

        lastButton = Gtk.Button("last", use_underline=True)
        lastButton.connect("clicked", self.next, False)
        CASBox.pack_start(lastButton, True, True, 0)

        self.entry = Gtk.Entry()
        self.entry.connect("changed", self.text_changed)
        CASBox.pack_start(self.entry, True, True, 0)

        nextButton = Gtk.Button("next", use_underline=True)
        nextButton.connect("clicked", self.next, True)
        CASBox.pack_start(nextButton, True, True, 0)

        commitButton = Gtk.Button("commit", use_underline=True)
        commitButton.connect("clicked", self.commit)
        CASBox.pack_start(commitButton, True, True, 0)

        self.scan()

    def toggle_select_all_images(self, sender):
        all_selected = all(image_button.selected for image_button, image_file in self.thumbnails)
        for image_button, image_file in self.thumbnails:
            image_button.selected = not all_selected

    def add_images(self, issue):
        for image_file in issue.files:
            print(image_file.filename)
            image_button = ThumbnailButton(image_file.filename)
            self.thumbnails.append((image_button, image_file))
            self.thumbnailgrid.add(image_button)

    def scan(self):
        for e in self.dbsession.query(Event).all():
            for p in e.photos:
                folders = p.filename.split("/")
                if ".jpg" in folders[3].lower():
                    folder = e.name  # folders[2] --ignore
                else:
                    folder = "/".join(folders[3:-1])

                if e.name is None:
                    if os.path.exists(p.filename):
                        print(folder + " # --kein event zugeordet!?--")
                    else:
                        print(p.filename + " was not found on disc!")

                elif folder != e.name:
                    if folder not in self._data:
                        self._data[folder] = Issue(folder, e, [p])
                    else:
                        self._data[folder].files.append(p)
        self.progressbar.set_fraction(0.0)
        self.progressbar.set_text("%s of %s" % (0, len(self._data)))
        self.progressbar.set_show_text(True)
        self._data_iter = iter(self._data)
        self.fill_view(next(self._data_iter))

    def fill_view(self, issue: Issue):
        print(issue.folder, issue.event)
        self.button[self._PATH].set_label("{0:^50}".format(issue.folder))
        self.button[self._EVENT].set_label("{0:^50}".format(issue.event.name))
        self.add_images(issue)

    def chose(self, button, chosen):
        if button.get_active() and not self.button[not chosen].get_active():
            self.entry.disconnect_by_func(self.text_changed)
            self.entry.set_text(self._data[self._data_iter][chosen])
            self.entry.connect("changed", self.text_changed)
        if self.button[not chosen].get_active() and not button.get_active():
            self.entry.disconnect_by_func(self.text_changed)
            self.entry.set_text(self._data[self._data_iter][not chosen])
            self.entry.connect("changed", self.text_changed)
        else:
            self.entry.disconnect_by_func(self.text_changed)
            self.entry.set_text("")
            self.entry.connect("changed", self.text_changed)

    def next(self, button, direction):
        if self.button[self._EVENT].get_active() or self.button[self._PATH].get_active():
            self.results[self._data_iter.key()] = (self.entry.get_text(), self._data_iter.this())
        else:
            self.results[self._data_iter.key()] = (None, self._data_iter.this())
        if direction:
            current = self._data_iter.next()
        else:
            current = self._data_iter.prev()
        self.button[self._PATH].set_label("{0:^50}".format(current[self._PATH]))
        self.button[self._EVENT].set_label("{0:^50}".format(current[self._EVENT]))
        self.progressbar.set_fraction((int(self._data_iter) + 1.0) / len(self._data))
        self.progressbar.set_text("%2s of %2s" % (int(self._data_iter), len(self._data)))
        if self._data_iter.key() in self.results:
            tmp = self.results[self._data_iter.key()]
            if tmp[0] is not None:
                self.button[self._PATH].set_active(tmp[0] == tmp[1][0])
                self.button[self._EVENT].set_active(tmp[0] == tmp[1][1])
                self.entry.set_text(tmp[0])
            else:
                self.entry.set_text("")
        else:
            self.button[self._PATH].set_active(False)
            self.button[self._EVENT].set_active(False)
            self.entry.set_text("")

    def text_changed(self, button):
        for g in (self._EVENT, self._PATH):
            self.button[g].disconnect_by_func(self.chose)
            self.button[g].set_active(False)
            self.button[g].connect("toggled", self.chose, g)

    def commit(self, button):
        for r in self.results.values():
            e = self.dbsession.query(Event).get(r[1][2].id)
            if r[0] is None:
                print("keep both %s and %s" % (r[1][self._PATH], r[1][self._EVENT]))
            else:
                if r[0] == "":
                    print("")
                    e = self.dbsession.query(Event).filter(Event.name.like())
                else:
                    if r[0] != r[1][self._EVENT]:
                        print("rename event %s to %s: " % (r[1][self._EVENT], r[0]))
                        e.name = r[0]
                        self.dbsession.merge(e)
                    if r[0] != r[1][self._PATH]:
                        prefix = "/".join(e.photos[0].filename.split("/")[:3])
                        dst = prefix + "/" + r[0]

                        print("move photos from %s to %s" % (prefix + r[1][self._PATH], dst))
                        try:
                            os.mkdir(dst)
                        except FileExistsError:
                            print("mkdir: %s already exists.." % dst)
                        for p in e.photos:
                            ph = self.dbsession.query(Photo).get(p.id)
                            oldfilename = ph.filename
                            ph.filename = dst + "/"+ ph.filename.split("/")[-1]
                            tryagain = True
                            while tryagain:
                                try:
                                    pass
                                    # os.rename(oldfilename, ph.filename)
                                    print("os.rename( %s, %s )" % (oldfilename,ph.filename))
                                    tryagain = False
                                except FileExistsError:
                                    print("os.rename: %s already existed!" % ph.filename)
                                    ph.filename = ph.filename.lower().replace(".jpg", "1.jpg")
                            # session.merge(ph)
                            # session.commit()

        self.dbsession.commit()
        self.results = {}
        self.scan()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Shotwell Event <-> Folder Sync")
    parser.add_argument("source", nargs="?", type=str, default="/home/poku/.local/share/shotwell/data/photo.db")
    args = parser.parse_args()

    engine = sql.create_engine("sqlite:///"+args.source)
    connection = engine.connect()
    Session = sql.orm.sessionmaker(bind=engine)

    win = ToggleButtonWindow(Session())
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()
