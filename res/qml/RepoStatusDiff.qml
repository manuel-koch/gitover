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

    DiffText {
        id: theDiff
        anchors.fill:  parent

        status:        root.status

        property CommitDetails details: CommitDetails {
            repository:  root.repository
            rev:         commit

            onDiffChanged: {
                theDiff.diff = diff
            }
        }

        function updateDiff() {
            if(path) {
                theDiff.diff = (root.repository !== null ? root.repository.diff(root.path,root.status,1024*512) : "")
            }
        }
    }
}
