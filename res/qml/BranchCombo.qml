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

Item {
    id: root

    property Repo repository: null
    property alias font: theCombo.font

    ComboBox {
        id: theCombo
        anchors.fill: parent
        flat:           true
        leftPadding:    0
        rightPadding:   0

        contentItem: Text {
            text:                theCombo.displayText
            font:                theCombo.font
            color:               "black"
            horizontalAlignment: Text.AlignLeft
            verticalAlignment:   Text.AlignVCenter
            elide:               Text.ElideRight
        }

        delegate: ItemDelegate {
            width:  theCombo.width
            height: theText.height + 2
            Text {
                id:         theText
                width:      theCombo.width
                topPadding: 1
                text:       modelData
                font:       root.font
                elide:      Text.ElideRight
            }
            highlighted: theCombo.highlightedIndex == index
        }

        indicator: Canvas {
            id: theCanvas
            x:           theCombo.width - width - theCombo.rightPadding
            y:           theCombo.topPadding + (theCombo.availableHeight - height) / 2
            width:       12
            height:      8
            contextType: "2d"

            Connections {
                target: theCombo
                onPressedChanged: theCanvas.requestPaint()
            }

            onPaint: {
                context.reset();
                context.moveTo(0, 0);
                context.lineTo(width, 0);
                context.lineTo(width / 2, height);
                context.closePath();
                context.strokeStyle = theCombo.pressed ? "#f8f8f8" : "black";
                context.stroke();
            }
        }

        function selectBranch(branch) {
            theCombo.currentIndex = theCombo.find(branch)
        }

        function useBranches(branch,branches) {
            var b = [branch]
            if( branches.length > 1 )
                b.push("---")
            for( var i=0; i<branches.length; i++ ) {
                if( b.indexOf(branches[i]) == -1 )
                    b.push( branches[i] )
            }
            theCombo.model = b
            theCombo.currentIndex = 0
        }

        Connections {
            target: repository
            onBranchChanged:   useBranches(repository.branch,repository.branches)
            onBranchesChanged: useBranches(repository.branch,repository.branches)
        }

        Component.onCompleted: useBranches(repository.branch,repository.branches)
    }

}
