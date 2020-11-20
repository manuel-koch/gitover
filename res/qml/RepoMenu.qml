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

Menu {
    id: theMenu
    title: repository != null ? repository.name : ""

    property Repo repository: null
    property bool shortcutsEnabled: true

    function fillMenu() {
        internal.commands = theMenu.repository ? theMenu.repository.cmds() : null
        internal.tools = theMenu.repository ? theMenu.repository.toolCmds() : null
    }

    onRepositoryChanged: fillMenu()

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
        MenuItem {
            text: internal.commands && index < internal.commands.length && internal.commands[index] ? internal.commands[index].title : ""
            shortcut: theMenu.shortcutsEnabled && internal.commands && index < internal.commands.length && internal.commands[index] ? internal.commands[index].shortcut : ""
            onTriggered: repository.execCmd(internal.commands[index].name)
        }
        onObjectAdded: theMenu.insertItem(index, object)
        onObjectRemoved: theMenu.removeItem(object)
    }

    MenuSeparator {
        visible: internal.tools && internal.tools.length
    }

    Instantiator {
        model: internal.tools
        MenuItem {
            text: internal.tools && index < internal.tools.length && internal.tools[index] ? internal.tools[index].title : ""
            shortcut: theMenu.shortcutsEnabled && internal.tools && index < internal.tools.length && internal.tools[index] ? internal.tools[index].shortcut : ""
            onTriggered: repository.execCmd(internal.tools[index].name)
        }
        onObjectAdded: theMenu.insertItem(index, object)
        onObjectRemoved: theMenu.removeItem(object)
    }
}
