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
import QtQuick 2.6
import QtQuick.Layouts 1.2
import QtQuick.Controls 1.4
import Gitover 1.0
import "."

Rectangle {
    id: root

    radius:        4
    border.width:  1
    border.color:  Theme.colors.border
    color:         "transparent"
    clip:          true

    property Repo repository: null

    ListView {
        id: theList
        anchors.fill:     parent
        anchors.margins:  2
        clip:             true
        snapMode:         ListView.SnapToItem
        boundsBehavior:   Flickable.StopAtBounds

        model: repository !== null ? repository.output : null

        headerPositioning: ListView.OverlayHeader
        header: Rectangle {
            z:      3
            radius: 4
            width:  theList.width
            height: theHeaderText.height
            color:  Theme.colors.statusHeaderBg
            visible: repository !== null
            Text {
                id: theHeaderText
                width:       theList.width
                text:        theList.count + " output lines :"
                leftPadding: 2
            }
        }

        delegate: Text {
            font.family:    "courier"
            font.pointSize: 10
            text:           timestamp + ": " + line
        }

        onCountChanged: theScrollTimer.restart()
    }

    Timer {
        id: theScrollTimer
        interval: 500
        onTriggered: theList.positionViewAtIndex(theList.count-1,ListView.End)
    }
}
