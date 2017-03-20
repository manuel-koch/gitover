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
import Gitover 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color:        "white"

    Timer {
        id: theRefreshTimer
        interval:    5*60*1000 // 5 minutes
        repeat:      true
        running:     true
        onTriggered: globalRepositories.refresh()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 2

        Text {
            Layout.fillWidth: true
            color:            "black"
            text:             globalRepositories.nofRepos + " Repos..."
        }

        Text {
            Layout.fillWidth: true
            textFormat:       Text.RichText
            text:             "<a href='refresh'>Refresh...</a>"
            onLinkActivated:  globalRepositories.refresh()
        }

        ListView {
            id: theRepoList
            Layout.fillWidth:  true
            Layout.fillHeight: true
            spacing:           2
            clip:              true
            snapMode:          ListView.SnapToItem
            boundsBehavior:    Flickable.StopAtBounds

            model: globalRepositories

            delegate: RepoView {
                repository: repo
                width:      theRepoList.width
                onClicked:  theRepoList.currentIndex = index
            }

            ScrollIndicator.vertical: ScrollIndicator { }

            onCurrentIndexChanged: console.debug("currentIndex",currentIndex)
        }
    }
}
