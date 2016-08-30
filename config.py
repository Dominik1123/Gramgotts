from pyhocon import ConfigFactory

# Use a copy of app.conf.template as app.conf and fill in the missing parameters
config = ConfigFactory.parse_file('app.conf')
