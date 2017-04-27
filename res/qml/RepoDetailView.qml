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

Rectangle {
    id: root

    border.width:  1
    border.color:  "silver"
    color:         "transparent"
    clip:          true

    property Repo repository: null

    Flickable {
        id: theFlickable
        anchors.fill:    root
        anchors.margins: 2
        contentWidth:    width
        contentHeight:   theColumns.implicitHeight

        ColumnLayout {
            id: theColumns
            width:   theFlickable.contentWidth
            spacing: 2
            Text {
                Layout.fillWidth: true
                text:             (root.repository !== null) ? repository.name : ""
                font.bold:        true
                font.pointSize:   14
            }
            Text {
                Layout.fillWidth: true
                text:             (root.repository !== null) ? repository.path : ""
                leftPadding:      10
                font.pointSize:   10
            }
            Text {
                Layout.fillWidth: true
                text:             "Local Branches :"
                font.bold:        true
                visible:          root.repository !== null
            }
            Repeater {
                Layout.fillWidth: true
                model:            repository != null ? repository.branches : null
                Text {
                    property bool obsolete: root.repository !== null && repository.mergedToTrunkBranches.indexOf(modelData)!=-1
                    text:           modelData + (obsolete ? " --> <i>(obsolete: already merged to trunk)</i>" : "")
                    leftPadding:    10
                    font.pointSize: 10
                }
            }
            Text {
                Layout.fillWidth: true
                text:             "Remote Branches :"
                font.bold:        true
                visible:          root.repository !== null && repository.remoteBranches.length
            }
            Repeater {
                Layout.fillWidth: true
                model:            repository != null ? repository.remoteBranches : null
                Text {
                    text:           modelData + " --> <a href='checkout'>checkout</a>"
                    leftPadding:    10
                    font.pointSize: 10
                    onLinkActivated: repository.triggerCheckoutBranch(modelData)
                }
            }
            BranchDetails {
                Layout.fillWidth: true
                title:            "Tracking" + ((repository != null && repository.trunkBranch == repository.trackingBranch) ? "/Trunk" : "") + " branch is " + (repository != null ? repository.trackingBranchAhead : 0)+ " commit(s) ahead :"
                repository:       root.repository
                commits:          repository != null ? repository.trackingBranchAheadCommits : null
                visible:          repository != null && repository.trackingBranchAhead
            }
            BranchDetails {
                Layout.fillWidth: true
                title:            "Tracking" + ((repository != null && repository.trunkBranch == repository.trackingBranch) ? "/Trunk" : "") + " branch is " + (repository != null ? repository.trackingBranchBehind : 0)+ " commit(s) behind :"
                repository:       root.repository
                commits:          repository != null ? repository.trackingBranchBehindCommits : null
                visible:          repository != null && repository.trackingBranchBehind
            }
            BranchDetails {
                Layout.fillWidth: true
                title:            "Trunk branch is " + (repository != null ? repository.trunkBranchAhead : 0)+ " commit(s) ahead :"
                repository:       root.repository
                commits:          repository != null ? repository.trunkBranchAheadCommits : null
                visible:          repository != null && repository.trunkBranchAhead && (repository.trunkBranch != repository.trackingBranch)
            }
            BranchDetails {
                Layout.fillWidth: true
                title:            "Trunk branch is " + (repository != null ? repository.trunkBranchBehind : 0)+ " commit(s) behind :"
                repository:       root.repository
                commits:          repository != null ? repository.trunkBranchBehindCommits : null
                visible:          repository != null && repository.trunkBranchBehind && (repository.trunkBranch != repository.trackingBranch)
            }
        }
    }
}
