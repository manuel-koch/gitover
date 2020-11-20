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
import QtQuick.Controls 2.3
import Gitover 1.0
import "."

Menu {
    id: theMenu
    title: repository != null ? repository.name : ""

    property Repo repository: null
    property string status: ""
    property string path: ""

    function fillMenu() {
        internal.commands = theMenu.repository ? theMenu.repository.statusCmds(theMenu.status) : null
        internal.tools = theMenu.repository ? theMenu.repository.statusToolCmds(theMenu.status) : null
    }

    onRepositoryChanged: fillMenu()
    onStatusChanged:     fillMenu()

    QtObject {
        id: internal
        property var commands: null
        property var tools: null
    }

    Connections {
        target: repository
        function onStatusUpdated() {
            fillMenu()
        }
    }

    Instantiator {
        model: internal.commands
        CustomMenuItem {
            text: internal.commands && index < internal.commands.length && internal.commands[index] ? internal.commands[index].title : ""
            onTriggered: repository.execStatusCmd(internal.commands[index].name, theMenu.status, theMenu.path)
        }
        onObjectAdded: theMenu.insertItem(index, object)
        onObjectRemoved: theMenu.removeItem(object)
    }

    Instantiator {
        model: internal.tools && internal.tools.length ? 1 : null
        MenuSeparator {
            contentItem: Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width-4
                implicitHeight: 1
                color: "silver"
            }
            background: Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: parent.width-4
                implicitHeight: 3
                color: "white"
            }
        }
        onObjectAdded: theMenu.insertItem(internal.commands.length, object)
        onObjectRemoved: theMenu.removeItem(object)
    }

    Instantiator {
        model: internal.tools
        CustomMenuItem {
            text: internal.tools && index < internal.tools.length && internal.tools[index] ? internal.tools[index].title : ""
            onTriggered: repository.execStatusCmd(internal.tools[index].name, theMenu.status, theMenu.path)
        }
        onObjectAdded: theMenu.insertItem(internal.commands.length + 1 + index, object)
        onObjectRemoved: theMenu.removeItem(object)
    }
}
