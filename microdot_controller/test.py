# ViperIDE - MicroPython Web IDE
# Read more: https://github.com/vshymanskyy/ViperIDE

# Connect your device and start creating! 🤖👨‍💻🕹️

# You can also open a virtual device and explore some examples:
# https://viper-ide.org?vm=1


import logging

log_level = logging.DEBUG
log_format = '%(asctime)s %(levelname)s %(name)s: %(message)s'

logging.basicConfig(level=log_level, format=log_format)
log = logging.getLogger("picoreflowd")

logging.debug("test - debug")  # ignored by default
logging.info("test - info")  # ignored by default
logging.warning("test - warning")
logging.error("test - error")
logging.critical("test - critical")