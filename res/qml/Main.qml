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
import "."

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
                onTriggered: theAddRepoDialog.openDialog()
            }
            MenuItem {
                text:        "About Gitover"
                onTriggered: theAboutDialog.openDialog()
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

    SelectDirectoryDialog {
        id: theAddRepoDialog
        title: "Please choose a git directory"
        onSelected: {
            console.log("You choose: " + url)
            globalRepositories.addRepoByUrl(url)
        }
    }

    AboutDialog {
        id: theAboutDialog
    }

    QtObject {
        id: internal
        property bool hasRepos: globalRepositories.nofRepos != 0
    }

    ColumnLayout {
        anchors.fill:    parent
        anchors.margins: 2
        spacing:         2

        Text {
            Layout.fillWidth:    true
            Layout.fillHeight:   true
            verticalAlignment:   Text.AlignVCenter
            horizontalAlignment: Text.AlignHCenter
            text:                "Display overview(s) by <a href='open'>opening</a> a git repository..."
            onLinkActivated:     theAddRepoDialog.openDialog()
            visible:             !internal.hasRepos
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
            visible:           internal.hasRepos

            property int cellSpacing: 2
            property int cellsPerRow: 5
            property Repo repository: null

            model: globalRepositories

            delegate: RepoView {
                repository: repo
                width:      theRepoGrid.cellWidth - ( isLastColumn ? 0 : theRepoGrid.cellSpacing)
                height:     theRepoGrid.cellHeight - ( isLastRow ? 0 : theRepoGrid.cellSpacing)
                onClicked:  theRepoGrid.currentIndex = index
                color:      isCurrent ? Theme.colors.selectedRepoBg : "transparent"
                property bool isCurrent:    theRepoGrid.currentIndex == index
                property int  column:       index % theRepoGrid.cellsPerRow
                property int  row:          Math.floor( index / theRepoGrid.cellsPerRow )
                property bool isLastColumn: (column+1) == theRepoGrid.cellsPerRow
                property bool isLastRow:    row == Math.floor(theRepoGrid.count / theRepoGrid.cellsPerRow)
            }

            onCurrentIndexChanged: {
                console.debug("currentIndex",currentIndex)
                theRepoGrid.repository = (currentIndex != -1) ? globalRepositories.repo( currentIndex ) : null
            }

            onCountChanged: currentIndex = -1
        }

        TabView {
            id: theTabView
            Layout.fillWidth:       true
            Layout.fillHeight:      false
            Layout.preferredHeight: root.height / 3
            visible:                internal.hasRepos
            Tab {
                title: "General"
                RepoDetailView {
                    id: theRepoDetail
                    repository: theRepoGrid.repository
                    visible:    internal.hasRepos
                }
            }
            Tab {
                title: "Status"
                RowLayout {
                    spacing: 2
                    RepoStatusList {
                        id: theRepoChanges
                        Layout.fillWidth:  true
                        Layout.fillHeight: true
                        repository:        theRepoGrid.repository
                        visible:           internal.hasRepos
                    }
                    RepoStatusDiff {
                        id: theStatusDiff
                        Layout.fillWidth:  true
                        Layout.fillHeight: true
                        repository:        theRepoGrid.repository
                        path:              theRepoChanges.currentPath
                        status:            theRepoChanges.currentStatus
                        visible:           internal.hasRepos
                    }
                }
            }
            Tab {
                title: "Output"
                RepoOutputList {
                    id: theRepoOutput
                    repository: theRepoGrid.repository
                    visible:    internal.hasRepos
                }
            }
        }
    }
}
