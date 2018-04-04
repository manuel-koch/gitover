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
// Copyright 2018 Manuel Koch
//
import QtQuick 2.6
import QtQuick.Layouts 1.2
import QtQuick.Controls 2.3
import Gitover 1.0
import "."

MenuItem {
    id: menuItem
    contentItem: Text {
                leftPadding: menuItem.indicator.width
                rightPadding: menuItem.arrow.width
                text: menuItem.text
                font: menuItem.font
                opacity: enabled ? 1.0 : 0.3
                color: "black"
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
    }
    background: Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width-4
                implicitWidth: 200
                anchors.verticalCenter: parent.verticalCenter
                height: parent.height-2
                implicitHeight: 18
                opacity: enabled ? 1 : 0.3
                color: menuItem.highlighted ? Theme.colors.selectedRepoBg : "transparent"
    }
}
