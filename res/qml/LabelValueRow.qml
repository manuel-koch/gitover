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

Item {
    id: root
    height: Math.max( theLabel.height, theContent.height )

    property alias label:     theLabel.text
    property real labelWidth: theLabel.implicitWidth + 2

    default property alias container: theContent.children

    RowLayout {
        id: theRow
        anchors.fill: parent
        spacing:      0

        Text {
            id: theLabel
            Layout.preferredWidth: root.labelWidth
            Layout.alignment:      Qt.AlignTop
            color:                 "black"
            font.pointSize:        10
        }
        Item {
            id: theContent
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            height:           childrenRect.height

            onChildrenChanged: {
                for(var i=0; i<children.length; i++) {
                    children[i].width = Qt.binding( function() { return theContent.width; })
                }
            }
        }
    }
}
