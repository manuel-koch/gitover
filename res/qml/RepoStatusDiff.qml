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
    property string commit: ""

    onRepositoryChanged: theDiff.updateDiff()
    onPathChanged:       theDiff.updateDiff()
    onStatusChanged:     theDiff.updateDiff()
    onCommitChanged:     theDiff.updateDiff()

    Connections {
        target: repository
        function onStatusUpdated() {
            theDiff.updateDiff()
        }
    }

    TextArea {
        id: theDiff
        anchors.fill:     parent
        readOnly:         true
        wrapMode:         TextEdit.NoWrap
        textFormat:       TextEdit.PlainText
        font.family:      "courier"
        selectByKeyboard: true
        selectByMouse:    true

        onTextChanged: {
            // scroll to top
            flickableItem.contentX = 0
            flickableItem.contentY = 0
        }

        function updateDiff() {
            text = (root.repository !== null ? root.repository.diff(commit || path,status,1024*512) : "")
        }
    }

    GitDiffFormatter {
        textDocument: (status=="committed" || status=="modified" || status=="staged" || status=="conflict") ? theDiff.textDocument : null
    }
}
