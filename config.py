from pyhocon import ConfigFactory

try:
    # Use a copy of app.conf.template as app.conf and fill in the missing parameters
    config = ConfigFactory.parse_file('app.conf')
except IOError:
    raise IOError("Use a copy of app.conf.template to create a valid application configuration named 'app.conf' " +
                  "and fill in the missing parameters")
