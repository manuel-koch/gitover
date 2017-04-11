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
    property string path: ""
    property string status: ""

    onRepositoryChanged: theDiff.updateDiff()
    onPathChanged:       theDiff.updateDiff()
    onStatusChanged:     theDiff.updateDiff()

    Connections {
        target: repository
        onStatusUpdated: theDiff.updateDiff()
    }

    Flickable {
        id: theFlickable
        anchors.fill:    root
        anchors.margins: 2
        contentWidth:    theDiff.implicitWidth
        contentHeight:   theDiff.implicitHeight
        boundsBehavior:  Flickable.StopAtBounds

        Text {
            id: theDiff

            onTextChanged: {
                theFlickable.contentX = 0
                theFlickable.contentY = 0
            }

            function updateDiff() {
                text = (root.repository !== null ? root.repository.diff(path,status) : "")
            }
        }
    }
}
