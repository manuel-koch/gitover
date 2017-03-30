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
import QtQuick.Controls 1.4
import QtQuick.Dialogs 1.2
import Gitover 1.0

ApplicationWindow {
    id: root
    width:   100
    height:  100
    visible: true

    menuBar: MenuBar {
        Menu {
            title: "File"
            MenuItem {
                text:        "\&Open repository"
                shortcut:    "Ctrl+O"
                onTriggered: theAddRepoDialog.open()
            }
            MenuItem {
                text:        "Quit"
                onTriggered: Qt.quit()
             }
        }
        Menu {
            title: "Repos"
            MenuItem {
                text: "Update status"
                shortcut: "Ctrl+R"
                onTriggered: globalRepositories.triggerUpdate()
            }
            MenuItem {
                text: "Fetch"
                shortcut: "Ctrl+F"
                onTriggered: globalRepositories.triggerFetch()
            }
        }
    }

    FileDialog {
        id: theAddRepoDialog
        title:          "Please choose a file"
        folder:         shortcuts.home
        selectFolder:   true
        selectExisting: true
        onAccepted: {
            console.log("You chose: " + theAddRepoDialog.fileUrls)
            globalRepositories.addRepoByUrl(theAddRepoDialog.fileUrls[0])
        }
    }

    ColumnLayout {
        anchors.fill:    parent
        anchors.margins: 2
        spacing:         2

        GridView {
            id: theRepoGrid
            Layout.fillWidth:  true
            Layout.fillHeight: true
            clip:              true
            cellWidth:         width / cellsPerRow
            cellHeight:        height / Math.ceil(count/cellsPerRow)
            snapMode:          GridView.SnapToRow
            boundsBehavior:    Flickable.StopAtBounds

            property int cellSpacing: 2
            property int cellsPerRow: 5

            model: globalRepositories

            delegate: RepoView {
                repository: repo
                width:      theRepoGrid.cellWidth - ( isLastColumn ? 0 : theRepoGrid.cellSpacing)
                height:     theRepoGrid.cellHeight - ( isLastRow ? 0 : theRepoGrid.cellSpacing)
                onClicked:  theRepoGrid.currentIndex = index
                color:      isCurrent ? "#fffeee" : "transparent"
                property bool isCurrent:    theRepoGrid.currentIndex == index
                property int  column:       index % theRepoGrid.cellsPerRow
                property int  row:          Math.floor( index / theRepoGrid.cellsPerRow )
                property bool isLastColumn: (column+1) == theRepoGrid.cellsPerRow
                property bool isLastRow:    row == Math.floor(theRepoGrid.count / theRepoGrid.cellsPerRow)
            }

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
