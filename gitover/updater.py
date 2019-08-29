# -*- coding: utf-8 -*-
"""
This file is part of Gitover.

Gitover is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Gitover is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Gitover. If not, see <http://www.gnu.org/licenses/>.

Copyright 2017 Manuel Koch

----------------------------

Helper to check for updates of Gitover.
"""
import logging

import requests

from gitover.utils import natural_sort_key

logger = logging.getLogger(__name__)


def get_latest_version():
    """
    :return: Tuple of version and url of latest GitOver release
    """
    url = "https://api.github.com/repos/manuel-koch/gitover/releases"
    logger.info(f"Searching latest release from {url}...")
    response = requests.get(url, headers={"Accept": "application/vnd.github.v3+json"})
    try:
        releases = response.json()
    except Exception as e:
        logger.exception(f"Failed to parse version response: {e!r}")
    if response.status_code == 200:
        tags = [
            (release["tag_name"].replace("v", ""), release["html_url"]) for release in releases
        ]
        tags.sort(key=natural_sort_key)
        return tags[-1]
    else:
        logger.error(f"Failed to get latest releases: {response.status_code}: {response.content}")
    return "", ""


def is_version_greater(v1, v2):
    """Returns true when v1 is considered greater than v2"""
    return v1 and v2 and natural_sort_key(v1) > natural_sort_key(v2)
