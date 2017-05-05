import os
import logging
import yaml

LOGGER = logging.getLogger(__name__)


class Config(object):
    """Wrap YAML formatted configuration"""

    CONFIG_NAME = ".gitover"

    def __init__(self):
        self._cfg = {}

    def _locate(self, dir="."):
        cfgDir = os.path.abspath(dir)
        while True:
            cfgPath = os.path.join(cfgDir, Config.CONFIG_NAME)
            if os.path.isfile(cfgPath):
                return cfgPath
            if cfgDir == "/":
                return None
            cfgDir = os.path.dirname(cfgDir)

    def load(self, dir="."):
        """Load configuration dict from YAML formatted file. Searching within
        current directory or parent directories."""
        self._cfg = {}
        cfgPath = self._locate(dir)
        if not cfgPath:
            LOGGER.debug("Failed to find config {}".format(Config.CONFIG_NAME))
            return False
        try:
            LOGGER.debug("Loading config from {}".format(cfgPath))
            self._cfg = yaml.load(open(cfgPath, "rb"))
            return True
        except:
            LOGGER.exception("Failed to load configuration {}".format(cfgPath))
            return False

    def general(self):
        """Returns dict of general options"""
        general = self._cfg.get("general", {})
        general["git"] = general.get("git", "")
        return general

    def tools(self):
        """Returns list of tools, where each entry is dict with keys name, title"""

        def _init_tool(tool):
            cmd = tool.get("cmd")
            if cmd:
                tool["name"] = tool.get("name", cmd.split()[0])
                tool["title"] = tool.get("title", cmd.split()[0])
                tool["shortcut"] = tool.get("shortcut", "")
            return tool

        return [_init_tool(tool) for tool in self._cfg.get("repo_commands", [])]

    def tool(self, name):
        """Returns detail configuration of named tool or None.
        Returns tool configuration as dict with keys name, title, cmd."""
        tools = [tool for tool in self.tools() if tool["name"] == name]
        if not tools:
            LOGGER.error("Unknown tool {}".format(name))
            return None
        return tools[0]
