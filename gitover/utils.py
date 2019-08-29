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

Utility functions.
"""
import re


def isiterable(item):
    try:
        it = iter(item)
    except TypeError:
        return False
    return True


def natural_sort_key(item):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    key = lambda i: [convert(c) for c in re.split("(\d+)", str(i))]
    if isinstance(item, str) or not isiterable(item):
        return key(item)
    else:
        return [key(i) for i in item]
