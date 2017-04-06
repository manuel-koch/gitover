// This file is part of Gitover.
//
// Gitover is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Gitover is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Gitover. If not, see <http://www.gnu.org/licenses/>.
//
// Copyright 2017 Manuel Koch
//
pragma Singleton
import QtQuick 2.6

Item {
    id: root

    property QtObject colors: theColors

    QtObject {
        id: theColors
        property color border:                "silver"
        property color selectedRepoBg:        "#FFFFC6"
        property color statusRepoUpgradeable: "green"
        property color statusRepoModified:    "yellow"
        property color statusStaged:          "#C1036E"
        property color statusConflict:        "#950000"
        property color statusModified:        "#007272"
        property color statusDeleted:         "#F00303"
        property color statusUntracked:       "#F06E03"
        property color statusHeaderBg:        "#ECECEC"
        property color statusSectionBg:       "#ACDBDD"
        property color branchAhead:           "green"
        property color branchBehind:          "red"
    }

    function colorValToHex(v) {
        v *= 255
        if( v < 16 )
            return "0" + v.toString(16)
        else
            return "" + v.toString(16)
    }

    function htmlColor(c) {
        return "#" + colorValToHex(c.r) + colorValToHex(c.g) + colorValToHex(c.b)
    }
}
