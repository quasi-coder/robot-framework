import pymongo

_AUTH_MECHANISM = 'MONGODB-CR'


class MongoConnectionManager(object):
    """
    Connection Manager handles the connection & disconnection to the database.
    """

    def __init__(self):
        """
        Initializes _dbconnection to None.
        """
        self._dbconnection = None

    def connect_to_mongodb(self, settings={}):
        """
        Loads pymongo and connects to the MongoDB host using parameters submitted.
        Settings dictionaty can contain following attributes:
          host -- database host name or url
          port -- database port
          username -- authorization username
          password -- authorization passwords
          max_pool_size -- max pool size
          network_timeout -- network timeout
          doc_class -- doc class
          tz_aware -- aware about timezone
          auth_database -- athorization database (see http://docs.mongodb.org/manual/core/authentication/#authentication-client-users for details)
        Example usage:
        | # To connect to foo.bar.org's MongoDB service on port 27017 |
        | Connect To MongoDB | ${settings} |

        """
        host = settings.get('host', 'localhost')
        port = int(settings.get('port', 27017))
        max_pool_size = int(settings.get('max_pool_size', 10))
        network_timeout = settings.get('network_timeout')
        doc_class = settings.get('doc_class', dict)
        tz_aware = settings.get('tz_aware', False)
        username = settings.get('username', 'admin')
        password = settings.get('password', 'admin')
        auth_database = settings.get('auth_database', 'admin')

        # print "host is               [ %s ]" % dbHost
        # print "port is               [ %s ]" % dbPort
        # print "pool_size is          [ %s ]" % dbPoolSize
        # print "timeout is            [ %s ]" % dbTimeout
        # print "slave_okay is         [ %s ]" % dbSlaveOkay
        # print "document_class is     [ %s ]" % dbDocClass
        # print "tz_aware is           [ %s ]" % dbTZAware
        print "| Connect To MongoDB | dbHost | dbPort | username | passwords | dbMaxPoolSize | dbNetworktimeout | dbDocClass | dbTZAware | auth_database |"
        print "| Connect To MongoDB | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            host, port, username, password, max_pool_size, network_timeout, doc_class, tz_aware, auth_database)

        self._dbconnection = _MongoClientWrapper(host=host, port=port, max_pool_size=max_pool_size,
                                                 network_timeout=network_timeout, document_class=doc_class,
                                                 tz_aware=tz_aware)
        if username:
            self._dbconnection[auth_database].authenticate(username, password)

    def disconnect_from_mongodb(self):
        """
        Disconnects from the MongoDB server.

        For example:
        | Disconnect From MongoDB | # disconnects from current connection to the MongoDB server |
        """
        print "| Disconnect From MongoDB |"
        self._dbconnection.close()


class _MongoClientWrapper(pymongo.MongoClient):
    '''
    Mediator between version 2.x and 3.x .
    '''

    def __init__(
            self,
            host=None,
            port=None,
            max_pool_size=100,
            network_timeout=10,
            document_class=dict,
            tz_aware=False,
            connect=True,
            **kwargs):

        if network_timeout:
            kwargs['socketTimeoutMS'] = network_timeout * 1000
        if pymongo.version_tuple[0] == 2:
            super(_MongoClientWrapper, self).__init__(host=host, port=port, max_pool_size=max_pool_size,
                                                      document_class=document_class, tz_aware=tz_aware,
                                                      _connect=connect, **kwargs)
        else:
            super(_MongoClientWrapper, self).__init__(host=host, port=port, document_class=document_class,
                                                      tz_aware=tz_aware, connect=connect, maxPoolSize=max_pool_size,
                                                      **kwargs)

    def disconnect(self):
        '''
        Method was deprecated in version 3.x in favour of MongoClient.close().
        '''
        close_ = getattr(pymongo.MongoClient, "disconnect", "close")
        close_(self)

    def end_request(self):
        '''
        Method was removed in version 3.x .
        '''
        end_request_ = getattr(pymongo.MongoClient, "end_request", None)
        if callable(end_request_):
            end_request_(self)
