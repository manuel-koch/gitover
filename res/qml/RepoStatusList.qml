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
    property string currentPath: ""
    property string currentStatus: ""

    RepoStatusMenu {
        id: theMenu
        repository:  root.repository
        path:        currentPath
        status:      currentStatus
    }

    Connections {
        target: repository
        onStatusUpdated: {
            theMenu.close()
            theList.selectEntry(theList.currentIndex)
        }
    }

    ListView {
        id: theList
        anchors.fill:             parent
        anchors.margins:          2
        clip:                     true
        snapMode:                 ListView.SnapToItem
        boundsBehavior:           Flickable.StopAtBounds

        model: repository !== null ? repository.changes : null

        onModelChanged: selectEntry(-1)

        onCountChanged: {
            if( currentIndex >= count )
                selectEntry(-1)
        }

        function selectEntry(index) {
            currentIndex = index
            if( currentIndex != -1) {
                var idx = model.index(currentIndex,0)
                root.currentPath = model.data(idx,ChangedFilesModel.Path)
                root.currentStatus = model.data(idx,ChangedFilesModel.Status)
             }
             else {
                root.currentPath = ""
                root.currentStatus = ""
             }
        }

        headerPositioning: ListView.OverlayHeader
        header: Rectangle {
            z:      3
            radius: 4
            width:  theList.width
            height: theHeaderText.height
            color:  Theme.colors.statusHeaderBg
            visible: repository !== null
            Text {
                id: theHeaderText
                width:       theList.width
                text:        theList.count + " changed files :"
                leftPadding: 2
            }
        }

        section.labelPositioning: ViewSection.InlineLabels
        section.property: "status"
        section.delegate: Rectangle {
            radius: 4
            width:  theList.width
            height: theSectionText.height
            color:  Theme.colors.statusSectionBg
            Text {
                id: theSectionText
                text:           section
                font.pointSize: Theme.fonts.smallPointSize
                leftPadding:    2
            }
        }

        highlightFollowsCurrentItem: true
        highlightMoveVelocity:       1000
        highlightResizeDuration:     0
        highlight: Rectangle {
            color: Theme.colors.selectedRepoBg
        }

        delegate: Item {
            width:  theList.width
            height: childrenRect.height
            Text {
                text:           path
                font.pointSize: Theme.fonts.smallPointSize
            }
            MouseArea {
                anchors.fill:    parent
                acceptedButtons: Qt.LeftButton | Qt.RightButton
                onClicked: {
                    theList.selectEntry(index)
                    if( mouse.button == Qt.RightButton ) {
                        theMenu.status = status
                        theMenu.path = path
                        theMenu.popup()
                    }
                }
            }
        }
    }
}
