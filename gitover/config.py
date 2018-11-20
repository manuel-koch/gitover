import multiprocessing
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

    def to_bool(self, value):
        return str(value).lower().strip() in ("yes", "true", "ok", "on")

    def general(self):
        """Returns dict of general options"""
        general = self._cfg.get("general", {})
        general["debug-log"] = general.get("debug-log", "")
        general["task-concurrency"] = int(general.get("task_concurrency",
                                                      multiprocessing.cpu_count() * 2))
        general["git"] = general.get("git", "")
        general["fswatch"] = general.get("fswatch", "fswatch")
        general["fswatch-singleton"] = self.to_bool(general.get("fswatch-singleton", "yes"))
        return general

    def _init_tool(self, tool):
        cmd = tool.get("cmd")
        if cmd:
            tool["name"] = tool.get("name", cmd.split()[0])
            tool["title"] = tool.get("title", cmd.split()[0])
            tool["shortcut"] = tool.get("shortcut", "")
        return tool

    def tools(self):
        """Returns list of tools, where each entry is dict with keys name, title and shortcut."""
        return [self._init_tool(tool) for tool in self._cfg.get("repo_commands", [])]

    def statusTools(self, status):
        """
        Returns list of status tools, where each entry is dict with keys name, title
        and shortcut.
        """
        return [self._init_tool(tool) for tool in
                self._cfg.get("status_commands", {}).get(status, [])]

    def tool(self, name):
        """
        Returns detail configuration of named tool or None.
        Returns tool configuration as dict with keys name, title, cmd and shortcut.
        """
        tools = [tool for tool in self.tools() if tool["name"] == name]
        if not tools:
            LOGGER.error("Unknown tool {}".format(name))
            return None
        return tools[0]

    def statusTool(self, status, name):
        """
        Returns detail configuration of named status tool or None.
        Returns tool configuration as dict with keys name, title, cmd and shortcut.
        """
        tools = [tool for tool in self.statusTools(status) if tool["name"] == name]
        if not tools:
            LOGGER.error("Unknown status {} tool {}".format(status, name))
            return None
        return tools[0]
