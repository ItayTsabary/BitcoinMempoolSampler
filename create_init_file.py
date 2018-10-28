import configparser

config = configparser.ConfigParser()

config['server'] = {'username': 'secret_username',
                    'password': 'secret_password',
                    'hostip': '127.0.0.1',
                    'portnum': 1234 }


config['output'] = {'data_dir_path' : "/some/path/to/save/files/at"}

with open('sampler_config.ini', 'w') as configfile:
  config.write(configfile)
