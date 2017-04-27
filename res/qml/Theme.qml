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

    // Base Color: 36B036 : http://paletton.com/#uid=72P1z0kmbrBcHF-i0vkqun+tEj5
    QtObject {
        id: theColors
        property color border:                "silver"
        property color selectedRepoBg:        "#FFF39C"
        property color statusRepoUpgradeable: "#097A09"
        property color statusRepoModified:    "#D18DB3"
        property color statusRepoError:       "#FE4E4E"
        property color statusAdded:           "#60DA60"
        property color statusStaged:          "#593896"
        property color statusConflict:        "#432182"
        property color statusModified:        "#007272"
        property color statusDeleted:         "#FA6D6D"
        property color statusUntracked:       "#9A81C9"
        property color statusHeaderBg:        "#ECECEC"
        property color statusSectionBg:       "#ACDBDD"
        property color branchAhead:           "#57C857"
        property color branchBehind:          "#BF2121"

        property color badgeText:     "white"
        property color badgeError:    "#BF2121"
        property color badgeStatus:   "#8095C7"
        property color badgeFetch:    "#6DAE1E"
        property color badgePull:     "#98690B"
        property color badgeCheckout: "#A41C53"
        property color badgeRebase:   "#BD3A6F"
        property color badgePush:     "#432182"
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

    function changeTypeToColor(change) {
        if( change == "M" )
            return theColors.statusModified
        if( change == "A" )
            return theColors.statusAdded
        if( change == "D" )
            return theColors.statusDeleted
        return "black"
    }
}
