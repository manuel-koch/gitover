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
import QtQuick.Controls 2.1
import Gitover 1.0

Rectangle {
    id: root

    height:        theColumn.implicitHeight + 2*radius
    radius:        4
    border.width:  1
    border.color:  "silver"
    color:         "transparent"
    clip:          true

    property Repo repository: null

    signal clicked()

    Component.onCompleted: console.debug(repository,repository.name)

    MouseArea {
        anchors.fill: parent
        onClicked: root.clicked()
    }

    Column {
        id: theColumn
        anchors.fill:     parent
        anchors.margins:  root.radius

        Text {
            id: theNameLabel
            width:          theColumn.width
            color:          "black"
            text:           root.repository ? root.repository.name : ""
            elide:          Text.ElideRight
            font.bold:      true
            font.pointSize: 12
        }
        RowLayout {
            id: theBranchRow
            width:  theColumn.width
            height: theBranchCombo.height

            Text {
                id: theBranchLabel
                Layout.preferredWidth: implicitWidth + 2
                color:                 "black"
                text:                  "Branch:"
                font.pointSize:        10
            }
            BranchCombo {
                id: theBranchCombo
                Layout.fillWidth: true
                height:           theBranchLabel.height
                repository:       root.repository
                font.pointSize:   theBranchLabel.font.pointSize
            }
        }
    }
}
