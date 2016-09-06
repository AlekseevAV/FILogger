import time
import logging
import sqlite3
from pyicloud.base import PyiCloudService, PyiCloudFailedLoginException

logging.basicConfig(filename='fil.log', level=logging.INFO,
                    format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s')


class FindIphoneLogger(object):
    """
    Base class
    """
    def __init__(self, login, password, request_period=10, device_name=False):
        """
        :param login: icloud.com login
        :param password: icloud.com password
        :param request_period: request location period (in minutes)
        :param device_name: device name from device settings
        """
        self.icloud_api = self.get_icloud_api(login, password)
        self.db_connect = self.get_db_connect()
        self.device_name = device_name
        self.device = self.get_device_object()
        self.request_period = request_period
        self.device_table_id = self.get_device_table_id()

    def get_device_object(self):
        """
        Find device with name from self.device_name
        :return: device object
        """
        logging.info('Finding device in icloud.com')
        if not self.device_name:
            self.device_name = self.icloud_api.iphone.data['name']
        for device in self.icloud_api.devices:
            if device.data['name'] == self.device_name:
                return device
        raise Exception('No device with name "{}" in icloud.com profile'.format(self.device_name))

    def get_device_table_id(self):
        """
        If self.device_id already in db return table device id (primary key). If not create device record and
        return id.
        :return: device table id
        """
        logging.info('Getting device_table_id')
        cursor = self.db_connect.cursor()
        result = cursor.execute('SELECT id FROM devices WHERE name=?', (self.device_name,)).fetchone()
        if not result:
            status = self.device.status()
            cursor.execute('INSERT INTO devices(device_id, display_name, name) VALUES (?, ?, ?)',
                           (self.icloud_api.iphone.data['id'], status['deviceDisplayName'], status['name']))
            result = cursor.execute('SELECT id FROM devices WHERE name=?', (self.device_name,)).fetchone()
            self.db_connect.commit()
        logging.info('device_table_id: ' + str(result[0]))
        return result[0]

    @staticmethod
    def get_db_connect():
        """
        If db already exist return connection, if not create db and return connection
        :return: db connection
        """
        logging.info('Connecting to db')
        con = sqlite3.connect('find_iphone_logger.db')
        cursor = con.cursor()
        if len(cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='devices';").fetchall()) == 0:
            cursor.execute("""CREATE TABLE devices (
                                                        id INTEGER PRIMARY KEY NOT NULL,
                                                        device_id VARCHAR NOT NULL,
                                                        display_name VARCHAR NOT NULL,
                                                        name VARCHAR NOT NULL
                                                    );""")
        if len(cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='locations';").fetchall()) == 0:
            cursor.execute("""CREATE TABLE locations
                                                (
                                                    id INTEGER PRIMARY KEY NOT NULL,
                                                    device INTEGER NOT NULL,
                                                    timeStamp INTEGER NOT NULL,
                                                    locationFinished INTEGER NOT NULL,
                                                    longitude REAL NOT NULL,
                                                    positionType VARCHAR,
                                                    locationType VARCHAR,
                                                    latitude REAL NOT NULL,
                                                    isOld INTEGER NOT NULL,
                                                    isInaccurate INTEGER NOT NULL,
                                                    horizontalAccuracy REAL NOT NULL,
                                                    FOREIGN KEY(device) REFERENCES devices(device_id) ON DELETE CASCADE
                                                );""")
        con.commit()
        return con

    def get_icloud_api(self, login, password):
        """
        :param login: icloud.com login
        :param password: icloud.com pass
        :return: icloud.com api connection
        """
        logging.info('Connecting to icloud.com')
        try:
            api = PyiCloudService(login, password)
        except not PyiCloudFailedLoginException:
            time.sleep(20)
            api = self.get_icloud_api(login, password)
        return api

    def db_saver(self, current_location):
        """
        Save location to db
        :param current_location: dict - response from icloud api (api.iphone.connection)
        """
        logging.info('Saving device location')
        cursor = self.db_connect.cursor()
        cursor.execute('INSERT INTO locations(device, timeStamp, locationFinished, longitude, positionType,'
                       ' locationType, latitude, isOld, horizontalAccuracy, isInaccurate) VALUES'
                       ' (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (self.device_table_id, current_location['timeStamp'], current_location['locationFinished'],
             current_location['longitude'], current_location['positionType'], current_location['locationType'],
             current_location['latitude'], current_location['isOld'], current_location['horizontalAccuracy'],
             current_location['isInaccurate']))
        self.db_connect.commit()

    def run(self):
        """
        main thread
        """
        logging.info('Running Logger')
        while True:
            current_device_location = self.device.location()
            if current_device_location:
                self.db_saver(current_device_location)
            else:
                logging.info('Location not found')
            logging.info('Waiting {} minutes ...'.format(str(self.request_period)))
            time.sleep(self.request_period * 60)


if __name__ == '__main__':
    import argparse
    import sys
    if sys.platform == 'linux2':
        import ctypes
        libc = ctypes.cdll.LoadLibrary('libc.so.6')
        libc.prctl(15, 'Find_IPhone_Logger', 0, 0, 0)
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', dest='username', help='Username from icloud.com', type=str, required=True)
    parser.add_argument('-p', dest='password', help='Password from icloud.com', type=str, required=True)
    parser.add_argument('-s', dest='request_period', help='Time between location requests (minutes)',
                        type=int, default=10)
    parser.add_argument('-n', dest='device_name', help='Device name', type=str, default=False)
    args = parser.parse_args()
    logger = FindIphoneLogger(args.username, args.password, args.request_period, args.device_name)
    logger.run()
