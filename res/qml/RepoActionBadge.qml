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

Item {
    id: root

    property alias text:     theLabel.text
    property alias fgColor:  theLabel.color
    property alias bgColor:  theBackground.color
    property alias autoHide: theHideTimer.interval

    implicitWidth: theLabel.implicitWidth

    Rectangle {
        id: theBackground
        anchors.fill: parent
        radius:       Math.ceil(theLabel.font.pixelSize * 0.4)
    }

    Text {
        id: theLabel
        anchors.centerIn: parent
        leftPadding:      text ? theBackground.radius * 0.8 : 0
        rightPadding:     text ? theBackground.radius * 0.8 : 0
        font.pixelSize:   Math.ceil( parent.height * 0.8 )
        font.bold:        true
    }

    Timer {
        id: theHideTimer
        interval:    0
        onTriggered: root.visible = false
        running:     root.text && root.visible && interval
    }
}
