class Path(object):
    def __init__(self, client):
        self.client = client

class ConfigurationPath(Path):
    def kit_configuration(self):
        return self.client.get("kit-configurations/")
