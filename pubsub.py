#
# simple publish-subscribe class
#

class pubsub(object) :

    def __init__(self) :
        self.listeners = []
        self.listener_index = 1

    def listen(self, fn, *args) :
        index = self.listener_index
        self.listener_index += 1
        self.listeners.append((index, fn, args))
        return index

    def unlisten(self, index) :
        for i in range(len(self.listeners)) :
            if self.listeners[i[0]]==index :
                self.listeners = self.listeners[:i-1] + self.listeners[i+1:]
                return True
        return False

    def signal(self, event=None) :
        for l in self.listeners :
            if event :
                l[1](event, *l[2])
            else :
                l[1](*l[2])
