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
import QtQuick 2.5
import QtQuick.Layouts 1.2
import QtQuick.Controls 2.1
import QtQuick.Dialogs 1.2
import Gitover 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color:        "white"

    FileDialog {
        id: theAddRepoDialog
        title: "Please choose a file"
        folder: shortcuts.home
        selectFolder: true
        selectExisting: true
        onAccepted: {
            console.log("You chose: " + theAddRepoDialog.fileUrls)
            globalRepositories.addRepoByUrl(theAddRepoDialog.fileUrls[0])
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 2

        Row {
            Layout.fillWidth:  true
            height: 20
            spacing: 8
            Text {
                visible: globalRepositories.nofRepos != 0
                color:   "black"
                text:    globalRepositories.nofRepos + " Repos..."
            }
            Text {
                visible:         globalRepositories.nofRepos != 0
                textFormat:      Text.RichText
                text:            "<a href='refresh'>Refresh...</a>"
                onLinkActivated: globalRepositories.triggerUpdate()
            }
            Text {
                visible:         globalRepositories.nofRepos != 0
                textFormat:      Text.RichText
                text:            "<a href='fetch'>Fetch...</a>"
                onLinkActivated: globalRepositories.triggerFetch()
            }
            Text {
                textFormat:      Text.RichText
                text:            "<a href='refresh'>Add repo...</a>"
                onLinkActivated: theAddRepoDialog.open()
            }
        }

        GridView {
            id: theRepoGrid
            Layout.fillWidth:  true
            Layout.fillHeight: true
            clip:              true
            cellWidth:         width / cellsPerRow
            cellHeight:        height / Math.ceil(count/cellsPerRow)
            snapMode:          GridView.SnapToRow
            boundsBehavior:    Flickable.StopAtBounds

            property int cellsPerRow: 5

            model: globalRepositories

            delegate: RepoView {
                repository: repo
                width:      theRepoGrid.cellWidth-2
                height:     theRepoGrid.cellHeight-2
                onClicked:  theRepoGrid.currentIndex = index
                color:      isCurrent ? "#fffeee" : "transparent"
                property bool isCurrent: theRepoGrid.currentIndex == index
            }

            // Doesn't work in frozen/bundled application
            //ScrollIndicator.vertical:   ScrollIndicator { }
            //ScrollIndicator.horizontal: ScrollIndicator { }

            onCurrentIndexChanged: {
                console.debug("currentIndex",currentIndex)
                if( currentIndex != -1 )
                    theRepoDetail.repository = globalRepositories.repo( currentIndex )
                else
                    theRepoDetail.repository = null
            }

            onCountChanged: currentIndex = -1
        }

        RepoDetailView {
            id: theRepoDetail
            repository: null
            Layout.fillWidth:  true
            Layout.preferredHeight: root.height / 3
        }
    }
}
