#
# Hack to make it easy to stop threads
#

from pubsub import pubsub

class stop_server(object) :

    my_pubsub = pubsub()

    @staticmethod
    def listen(fn, *args) :
        stop_server.my_pubsub.listen(fn, *args)

    @staticmethod
    def stop() :
        stop_server.my_pubsub.signal()
