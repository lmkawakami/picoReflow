import json
_config_file = "pid_config.json"
class _PIDConfig:
    def get_pid_config(self):
        """
        Returns the PID configuration parameters.
        """
        with open(_config_file, 'r') as file:
            config = json.load(file)
            return {
                "ki": config.get("ki"),
                "kd": config.get("kd"),
                "kp": config.get("kp")
            }

    def set_config(self,name, value):
        """
        Sets the PID configuration parameter.
        :param name: The name of the parameter (ki, kd, kp).
        :param value: The value to set for the parameter.
        """
        with open(_config_file, 'r') as file:
            config = json.load(file)
        
        if name in config:
            config[name] = value
            with open(_config_file, 'w') as file:
                json.dump(config, file)

    @property
    def pid_ki(self):
        """
        Returns the PID ki parameter.
        """
        return self.get_pid_config().get("ki")

    @property
    def pid_kd(self):
        """
        Returns the PID kd parameter.
        """
        return self.get_pid_config().get("kd")

    @property
    def pid_kp(self):
        """
        Returns the PID kp parameter.
        """
        return self.get_pid_config().get("kp")

pid_config = _PIDConfig()