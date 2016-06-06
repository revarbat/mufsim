from collections import namedtuple


MufEvent = namedtuple('Event', ['name', 'data'])


class MufEventQueue(object):
    def __init__(self):
        self.events = []

    def add_event(self, eventname, eventdata):
        event = MufEvent(name=eventname, data=eventdata)
        self.events.append(event)

    def find_event(self, eventnames):
        for idx, event in enumerate(self.events):
            if event.name in eventnames:
                return event
        return None

    def add_singleton_event(self, eventname, eventdata, replace=True):
        event = self.find_event([eventname])
        if event is None:
            self.add_event(eventname, eventdata)
        if replace:
            event.data = eventdata

    def count(self, pat):
        if pat == '*':
            return len(self.events)
        cnt = 0
        for event in self.events:
            if util.smatch(pat, event.name):
                cnt += 1
        return cnt


# vim: expandtab tabstop=4 shiftwidth=4 softtabstop=4 nowrap
