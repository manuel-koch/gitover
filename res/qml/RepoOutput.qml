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

    TextArea {
        id: theOutput
        anchors.fill:     parent
        anchors.margins:  2
        readOnly:         true
        wrapMode:         TextEdit.NoWrap
        font.family:      "courier"
        selectByKeyboard: true
        selectByMouse:    true

        property bool hasVertScroll:   height < contentHeight
        property int  vertScrollWidth: hasVertScroll ? width - viewport.width : 0

        function appendLines(first,last) {
            for( var i=first; i<=last; i++ ) {
                var idx = repository.output.index(i,0)
                var timestamp = repository.output.data(idx,OutputModel.Timestamp)
                var line = repository.output.data(idx,OutputModel.Line)
                theOutput.append(timestamp+": "+line)
            }
            if( !selectedText ) {
                // scroll to last line if nothing is selected
                flickableItem.contentX = 0
                flickableItem.contentY = Math.max(0,contentHeight - flickableItem.height)
            }
        }

        function updateAllLines() {
            cursorPosition = 0
            text = ""
            if( repository != null ) {
                appendLines(0,repository.output.count-1)
            }
        }
    }

    Rectangle {
        anchors.right:       parent.right
        anchors.top:         parent.top
        anchors.rightMargin: 4 + theOutput.vertScrollWidth
        anchors.topMargin:   4
        width:               theClearText.implicitWidth+4
        height:              theClearText.implicitHeight+2
        color:               Qt.rgba(1,1,1,0.8)
        radius:              4
        visible:             repository ? repository.output.count : false
        Text {
            id: theClearText
            anchors.centerIn: parent
            text: "<a href='clear'>clear</a>"
            onLinkActivated: repository.output.clearOutput()
        }
    }

    Text {
        anchors.centerIn: parent
        text:             repository ? "No output yet..." : "Select a repository to view output..."
        visible:          repository ? !repository.output.count : true
    }

    onRepositoryChanged:   theOutput.updateAllLines()
    Component.onCompleted: theOutput.updateAllLines()

    Connections {
        target: repository ? repository.output : null
        onRowsInserted: theOutput.appendLines(first,last)
        onModelReset:   theOutput.updateAllLines()
    }
}
