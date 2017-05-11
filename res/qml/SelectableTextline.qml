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

    implicitHeight: theText.implicitHeight
    implicitWidth:  theText.implicitWidth + (theLabel.visible ? theRow.spacing + theLabel.implicitWidth : 0)

    property alias text:        theText.text
    property alias label:       theLabel.text
    property alias font:        theText.font
    property alias leftPadding: theText.leftPadding

    signal linkActivated(string link)

    RowLayout {
        id: theRow
        anchors.fill: parent

        TextInput {
            id: theText
            Layout.fillWidth:      true
            Layout.maximumWidth:   implicitWidth
            readOnly:              true
            selectByMouse:         true
            clip:                  true
            onTextChanged:         ensureVisible(0)
            Component.onCompleted: ensureVisible(0)
            onWidthChanged:        ensureVisible(0)
        }
        Text {
            id: theLabel
            Layout.fillWidth: true
            font:             theText.font
            visible:          text != ""
            onLinkActivated:  root.linkActivated(link)
        }
    }
}
