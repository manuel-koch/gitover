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
// Copyright 2020 Manuel Koch
//
import QtQuick 2.6
import QtQuick.Layouts 1.2
import QtQuick.Controls 2.5
import Gitover 1.0
import "."

Rectangle {
    id: root

    radius:        4
    border.width:  1
    border.color:  Theme.colors.border
    color:         "transparent"
    clip:          true

    property string diff: null
    property string status: ""

    onDiffChanged: {
        // Cluster whole diff text into chunks of n lines to improve text performance for huge diff texts
        // Otherwise TextArea will freeze whole application trying to render all diff text in QML.
        var linesPerChunk = 250;
        var chunks = []
        var currLines = []
        var lines = diff ? diff.split("\n") : [];
        for(var i=0; i<lines.length; i++) {
            if( currLines.length == linesPerChunk ) {
                chunks.push(currLines.join("\n").trim())
                currLines = []
            } else {
                currLines.push(lines[i])
            }
        }
        if(currLines.length) {
            chunks.push( currLines.join("\n").trim() )
        }
        theListView.model = chunks
        theListView.positionViewAtBeginning()
    }

    ListView {
        id: theListView
        anchors {
            fill:    parent
            margins: root.radius-1
        }
        delegate: TextArea {
            id:               theTextArea
            width:            theListView.width
            height:           theListView.count <= 1 ? Math.max(theListView.height,implicitHeight) : implicitHeight
            text:             model.modelData
            activeFocusOnTab: false
            readOnly:         true
            wrapMode:         TextEdit.WrapAnywhere
            textFormat:       TextEdit.PlainText
            font.pixelSize:   10
            font.family:      "courier"
            selectByKeyboard: true
            selectByMouse:    true
            topPadding:       0
            bottomPadding:    0
            background: Rectangle {
                color: "white";
            }
            GitDiffFormatter {
                textDocument: (root.status=="committed" || root.status=="modified" || root.status=="staged" || root.status=="conflict") ? theTextArea.textDocument : null
            }
        }

        ScrollBar.horizontal: ScrollBar {}
        ScrollBar.vertical: ScrollBar {}
    }
}