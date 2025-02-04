import configparser

class Config:
    __conf = None

    @staticmethod
    def config():
        if Config.__conf is None:
            Config.__conf = configparser.ConfigParser()
            Config.__conf.read('pysensor.conf')

        return Config.__conf
