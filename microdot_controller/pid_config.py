import json
config_file = "pid_config.json"


class PIDConfig:
    @staticmethod
    def get_pid_config():
        """
        Returns the PID configuration parameters.
        """
        with open(config_file, 'r') as file:
            config = json.load(file)
            return {
                "ki": config.get("ki"),
                "kd": config.get("kd"),
                "kp": config.get("kp")
            }

    @staticmethod
    def set_config(name, value):
        """
        Sets the PID configuration parameter.
        :param name: The name of the parameter (ki, kd, kp).
        :param value: The value to set for the parameter.
        """
        with open(config_file, 'r') as file:
            config = json.load(file)
        
        if name in config:
            config[name] = value
            with open(config_file, 'w') as file:
                json.dump(config, file)

    @staticmethod
    @property
    def pid_ki():
        """
        Returns the PID ki parameter.
        """
        return PIDConfig.get_pid_config().get("ki")

    @staticmethod
    @property
    def pid_kd():
        """
        Returns the PID kd parameter.
        """
        return PIDConfig.get_pid_config().get("kd")

    @staticmethod
    @property
    def pid_kp():
        """
        Returns the PID kp parameter.
        """
        return PIDConfig.get_pid_config().get("kp")
