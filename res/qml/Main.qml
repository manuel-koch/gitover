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
        id: theMenuBar
        Menu {
            title: "File"
            MenuItem {
                text:        "\&New Window"
                shortcut:    "Ctrl+N"
                onTriggered: globalLauncher.openNewWindow("")
            }

            MenuItem {
                text:        "\&Open repository"
                shortcut:    "Ctrl+O"
                onTriggered: theAddRepoDialog.openDialog()
            }

            Menu {
                id: recentReposMenu
                title: "Open recent repository..."
                Instantiator {
                    model: globalRepositories.recentRepos
                    MenuItem {
                        text: index < globalRepositories.recentRepos.length && globalRepositories.recentRepos[index] ? globalRepositories.recentRepos[index].title + " ( " + globalRepositories.recentRepos[index].subtitle + " )" : ""
                        onTriggered: globalRepositories.addRepoByPath(globalRepositories.recentRepos[index].path)
                    }
                    onObjectAdded: recentReposMenu.insertItem(index, object)
                    onObjectRemoved: recentReposMenu.removeItem(object)
                }
            }

            MenuItem {
                text:        "About Gitover"
                onTriggered: theAboutDialog.openDialog()
            }
            MenuItem {
                text:        "Quit"
                onTriggered: root.close()
            }
        }
        Menu {
            title: "Repos"
            MenuItem {
                text: "Update status"
                shortcut: "Alt+R"
                onTriggered: globalRepositories.triggerUpdate()
            }
            MenuItem {
                text: "Fetch"
                shortcut: "Alt+F"
                onTriggered: globalRepositories.triggerFetch()
            }
        }
        RepoMenu {
            id: theRepoMenu
            visible: repository != null
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

    Rectangle {
        id: theUpdateBg
        visible:        globalVersionCanUpdate || globalVersionExperimental
        anchors.top:    parent.top
        anchors.left:   parent.left
        anchors.right:  parent.right
        height:         visible ? theUpdateText.implicitHeight + 4 : 0
        color:          Theme.colors.warningMsgBg
        Text {
            id: theUpdateText
            anchors.centerIn:     parent
            width:                parent.width

            horizontalAlignment:  Text.AlignHCenter
            verticalAlignment:    Text.AlignVCenter
            textFormat:           Text.RichText
            text:                 "You are using <i>Gitover</i> " + globalVersion + ", latest released version is <a href='update'>" + globalLatestVersion + "</a>."
            onLinkActivated:      { console.info(globalLatestVersionUrl); Qt.openUrlExternally(globalLatestVersionUrl) }
        }
    }

    SplitView {
        anchors.top:     theUpdateBg.bottom
        anchors.left:    parent.left
        anchors.right:   parent.right
        anchors.bottom:  parent.bottom
        anchors.margins: 2
        orientation:     Qt.Vertical

        handleDelegate: Item { height: 2 } // don't want a visible handle

        GridView {
            id: theRepoGrid
            Layout.minimumHeight: minCellHeight*cellsPerCol
            Layout.fillHeight:    true
            clip:                 true
            cellWidth:            calcCellWidth(cellsPerRow)
            cellHeight:           calcCellHeight(cellsPerRow)
            snapMode:             GridView.SnapToRow
            boundsBehavior:       Flickable.StopAtBounds
            visible:              internal.hasRepos

            property int cellSpacing: 2
            property int cellsPerRow: 1
            property int cellsPerCol: Math.ceil(count/cellsPerRow)
            property var minCellHeights: []
            property real minCellHeight: 1e6
            property Repo repository: null

            model: globalRepositories

            delegate: RepoView {
                repository:   repo
                width:        theRepoGrid.cellWidth - ( isLastColumn ? 0 : theRepoGrid.cellSpacing)
                height:       theRepoGrid.cellHeight - ( isLastRow ? 0 : theRepoGrid.cellSpacing)
                onClicked:    theRepoGrid.currentIndex = index
                onShowOutput: theTabView.selectTab("Output")
                color:        isCurrent ? Theme.colors.selectedRepoBg : "transparent"
                property bool isCurrent:    theRepoGrid.currentIndex == index
                property int  column:       index % theRepoGrid.cellsPerRow
                property int  row:          Math.floor( index / theRepoGrid.cellsPerRow )
                property bool isLastColumn: (column+1) == theRepoGrid.cellsPerRow
                property bool isLastRow:    row == Math.floor(theRepoGrid.count / theRepoGrid.cellsPerRow)
                onImplicitHeightChanged:    theRepoGrid.updateMinCellHeight(index,implicitHeight)
            }

            onCurrentIndexChanged: {
                theRepoGrid.repository = (currentIndex != -1) ? globalRepositories.repo( currentIndex ) : null
                theRepoMenu.repository = theRepoGrid.repository
            }

            onCountChanged: {
                currentIndex = -1
                findBestLayout()
            }

            onWidthChanged:         theRelayoutTimer.restart()
            onHeightChanged:        theRelayoutTimer.restart()
            onMinCellHeightChanged: theRelayoutTimer.restart()

            Timer {
                id: theRelayoutTimer
                interval:    300
                onTriggered: theRepoGrid.findBestLayout()
            }

            function updateMinCellHeight(idx,height) {
                while( minCellHeights.length <= idx )
                    minCellHeights.push(1e6)
                minCellHeights[idx] = height
                var min = 1e6
                for( var i=0; i<minCellHeights.length; i++ )
                    min = Math.min(min,minCellHeights[i])
                minCellHeight = min
            }

            function calcCellWidth(cols) {
                return width / cols
            }

            function calcCellHeight(cols) {
                return height / Math.ceil(count/cols)
            }

            function findBestLayout() {
                var dims = Array()
                for( var cols=1; cols<=count; cols++ ) {
                    var w = calcCellWidth(cols)
                    var h = calcCellHeight(cols)
                    if( w > minCellHeight*1.5 && h > minCellHeight ) {
                        dims.push({"cols": cols, "width": w, "height": h})
                    }
                }

                // sort by ascending area
                dims.sort(function(a,b) { return (b.width*b.height) - (a.width*a.height) })

                if( dims.length ) {
                    // pick the layout with the greatest area per cell
                    theRepoGrid.cellsPerRow = dims[0].cols
                }
            }
        }

        TabView {
            id: theTabView
            Layout.minimumHeight:   100
            Layout.fillHeight:      true
            Layout.preferredHeight: root.height / 3
            visible:                internal.hasRepos

            function selectTab(title) {
                for( var i=0; i<count; i++ ) {
                    if( getTab(i).title == title )
                        currentIndex = i
                }
            }

            Tab {
                title: "General"
                RepoDetailView {
                    id: theRepoDetail
                    repository: theRepoGrid.repository
                    visible:    internal.hasRepos
                }
            }
            Tab {
                title: "History"
                ColumnLayout {
                    anchors.fill:      parent
                    anchors.topMargin: 2
                    spacing:           2
                    Text {
                        text:           theRepoGrid.repository != null ? " Branch : " + theRepoGrid.repository.branch : ""
                        font.bold:      true
                        font.pointSize: 14
                    }
                    RepoCommitList {
                        Layout.fillWidth:  true
                        Layout.fillHeight: true
                        repository:       theRepoGrid.repository
                        visible:          theRepoGrid.repository != null
                    }
                }
            }
            Tab {
                title: "Status"
                SplitView {
                    RepoStatusList {
                        id: theRepoChanges
                        Layout.minimumWidth: 200
                        Layout.fillHeight:   true
                        repository:          theRepoGrid.repository
                        visible:             internal.hasRepos
                    }
                    RepoStatusDiff {
                        id: theStatusDiff
                        Layout.minimumWidth: 200
                        Layout.fillHeight:   true
                        repository:          theRepoGrid.repository
                        path:                theRepoChanges.currentPath
                        status:              theRepoChanges.currentStatus
                        visible:             internal.hasRepos
                    }
                }
            }
            Tab {
                title: "Trunk / Tracking"
                TabView {
                    id: theTabView
                    Layout.fillWidth:  true
                    Layout.fillHeight: true
                    Tab {
                        title: "Trunk " + (theRepoGrid.repository != null ? theRepoGrid.repository.trunkBranchAhead : 0) + " ahead"
                        ColumnLayout {
                            anchors.fill:      parent
                            anchors.topMargin: 2
                            spacing:           2
                            Text {
                                text:           "Trunk branch is " + (theRepoGrid.repository != null ? theRepoGrid.repository.trunkBranchAhead : 0) + " commit(s) ahead :"
                                font.bold:      true
                                font.pointSize: 14
                                visible:        theRepoGrid.repository != null
                            }
                            RepoCommitList {
                                Layout.fillWidth:  true
                                Layout.fillHeight: true
                                repository:       theRepoGrid.repository
                                commits:          theRepoGrid.repository != null ? theRepoGrid.repository.trunkBranchAheadCommits : null
                                visible:          theRepoGrid.repository != null
                            }
                        }
                    }
                    Tab {
                        title: "Trunk " + (theRepoGrid.repository != null ? theRepoGrid.repository.trunkBranchBehind : 0) + " behind"
                        ColumnLayout {
                            anchors.fill:      parent
                            anchors.topMargin: 2
                            spacing:           2
                            Text {
                                text:           "Trunk branch is " + (theRepoGrid.repository != null ? theRepoGrid.repository.trunkBranchBehind : 0) + " commit(s) behind :"
                                font.bold:      true
                                font.pointSize: 14
                                visible:        theRepoGrid.repository != null
                            }
                            RepoCommitList {
                                Layout.fillWidth:  true
                                Layout.fillHeight: true
                                repository:       theRepoGrid.repository
                                commits:          theRepoGrid.repository != null ? theRepoGrid.repository.trunkBranchBehindCommits : null
                                visible:          theRepoGrid.repository != null
                            }
                        }
                    }
                    Tab {
                        title: "Tracking " + (theRepoGrid.repository != null ? theRepoGrid.repository.trackingBranchAhead : 0) + " ahead"
                        ColumnLayout {
                            anchors.fill:      parent
                            anchors.topMargin: 2
                            spacing:           2
                            Text {
                                text:           "Tracking branch is " + (theRepoGrid.repository != null ? theRepoGrid.repository.trackingBranchAhead : 0) + " commit(s) ahead :"
                                font.bold:      true
                                font.pointSize: 14
                                visible:        theRepoGrid.repository != null
                            }
                            RepoCommitList {
                                Layout.fillWidth:  true
                                Layout.fillHeight: true
                                repository:       theRepoGrid.repository
                                commits:          theRepoGrid.repository != null ? theRepoGrid.repository.trackingBranchAheadCommits : null
                                visible:          theRepoGrid.repository != null
                            }
                        }
                    }
                    Tab {
                        title: "Tracking " + (theRepoGrid.repository != null ? theRepoGrid.repository.trackingBranchBehind : 0) + " behind"
                        ColumnLayout {
                            anchors.fill:      parent
                            anchors.topMargin: 2
                            spacing:           2
                            Text {
                                text:           "Tracking branch is " + (theRepoGrid.repository != null ? theRepoGrid.repository.trackingBranchBehind : 0) + " commit(s) behind :"
                                font.bold:      true
                                font.pointSize: 14
                                visible:        theRepoGrid.repository != null
                            }
                            RepoCommitList {
                                Layout.fillWidth:  true
                                Layout.fillHeight: true
                                repository:       theRepoGrid.repository
                                commits:          theRepoGrid.repository != null ? theRepoGrid.repository.trackingBranchBehindCommits : null
                                visible:          theRepoGrid.repository != null
                            }
                        }
                    }
                }
            }
            Tab {
                title: "Output"
                RepoOutput {
                    id: theRepoOutput
                    repository: theRepoGrid.repository
                    visible:    internal.hasRepos
                }
            }
        }
    }

    Text {
        anchors.centerIn: parent
        text:             "Display overviews by <a href='open'>opening</a> a git repository..."
        visible:          !internal.hasRepos
        onLinkActivated:  theAddRepoDialog.openDialog()
    }
}
