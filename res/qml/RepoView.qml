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

    height:        theColumn.implicitHeight + 2*radius
    radius:        4
    border.width:  internal.hasChanges || internal.canUpgrade ? 2 : 1
    border.color:  internal.hasChanges ? Theme.colors.statusRepoModified
                       : (internal.canUpgrade ? Theme.colors.statusRepoUpgradeable : Theme.colors.border)
    color:         "transparent"
    clip:          true

    property Repo repository: null

    signal clicked()
    signal showOutput()

    Component.onCompleted: console.debug(repository,repository.name)

    Connections {
        target: repository
        onError: {
            theErrorBadge.text = msg
            theErrorBadge.visible = true
        }
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: {
            if( mouse.button == Qt.RightButton ) {
                theMenu.fillMenu()
                theMenu.popup()
            }
            else {
                root.clicked()
            }
        }
        onDoubleClicked: repository.triggerUpdate()
    }

    Menu {
        id: theMenu

        property var dynMenuItems: [] // array of dynamically created MenuItem instances

        function clearMenu() {
            while(dynMenuItems.length) {
                var item = dynMenuItems.pop()
                theMenu.removeItem(item)
                item.destroy()
            }
        }

        function fillMenu() {
            clearMenu()
            var cmds = repository.cmds()
            for(var i=0; i<cmds.length; i++) {
                var newMenuItem
                if( cmds[i].title ) {
                    console.debug("Creating menu '"+cmds[i].title+"' for",repository.name)
                    newMenuItem = Qt.createQmlObject('import QtQuick.Controls 1.4; MenuItem {text: "'+cmds[i].title+'"; onTriggered: repository.execCmd("'+cmds[i].name+'")}',
                                                     theMenu, "dynamicMenuItem"+i);
                }
                else {
                    console.debug("Creating menu separator")
                    newMenuItem = Qt.createQmlObject('import QtQuick.Controls 1.4; MenuSeparator {}',
                                                     theMenu, "dynamicMenuItem"+i);
                }
                theMenu.insertItem(i,newMenuItem)
                dynMenuItems.push(newMenuItem)
            }
        }
    }

    QtObject {
        id: internal
        property real titleFontSize: 12
        property real labelFontSize: 10
        property real labelWidth:    50

        property bool hasChanges: untracked || modified || deleted || conflicts || staged
        property bool canUpgrade: root.repository && root.repository.trunkBranchAhead
        property int untracked:   root.repository ? root.repository.untracked : 0
        property int modified:    root.repository ? root.repository.modified : 0
        property int deleted:     root.repository ? root.repository.deleted : 0
        property int conflicts:   root.repository ? root.repository.conflicts : 0
        property int staged:      root.repository ? root.repository.staged : 0

        property string changeSummary: getChangeSummary(modified,deleted,untracked,conflicts,staged)

        function getChangeSummary(m,d,u,c,s) {
            var t = []
            if( s )
                t.push("<font color='"+Theme.htmlColor(Theme.colors.statusStaged)+"'>"+s+"-S</font>")
            if( c )
                t.push("<font color='"+Theme.htmlColor(Theme.colors.statusConflict)+"'>"+c+"-C</font>")
            if( m )
                t.push("<font color='"+Theme.htmlColor(Theme.colors.statusModified)+"'>"+m+"-M</font>")
            if( d )
                t.push("<font color='"+Theme.htmlColor(Theme.colors.statusDeleted)+"'>"+d+"-D</font>")
            if( u )
                t.push("<font color='"+Theme.htmlColor(Theme.colors.statusUntracked)+"'>"+u+"-U</font>")
            if( !m && !d && !u && !c && !s)
                t.push("<font color='#03C003'>up-to-date</font>")
            return t.join(", ")
        }
    }

    Column {
        id: theColumn
        anchors.fill:     parent
        anchors.margins:  root.radius
        spacing:          2

        RowLayout {
            width:   theColumn.width
            height:  theNameLabel.height
            spacing: 2
            Text {
                id: theNameLabel
                Layout.fillWidth:       true
                Layout.preferredHeight: 16
                color:                  "black"
                text:                   root.repository ? root.repository.name : ""
                elide:                  Text.ElideRight
                verticalAlignment:      Text.AlignVCenter
                font.bold:              true
                font.pointSize:         internal.titleFontSize
            }
            RepoActionBadge {
                id: theStatusBadge
                Layout.preferredHeight: theNameLabel.height
                text:                   "Status"
                fgColor:                Theme.colors.badgeText
                bgColor:                Theme.colors.badgeStatus
                visible:                root.repository && root.repository.updating
            }
            RepoActionBadge {
                id: theFetchBadge
                Layout.preferredHeight: theNameLabel.height
                text:                   "Fetch"
                fgColor:                Theme.colors.badgeText
                bgColor:                Theme.colors.badgeFetch
                visible:                root.repository && root.repository.fetching
            }
            RepoActionBadge {
                id: thePullBadge
                Layout.preferredHeight: theNameLabel.height
                text:                   "Pull"
                fgColor:                Theme.colors.badgeText
                bgColor:                Theme.colors.badgePull
                visible:                root.repository && root.repository.pulling
            }
            RepoActionBadge {
                id: theCheckoutBadge
                Layout.preferredHeight: theNameLabel.height
                text:                   "Checkout"
                fgColor:                Theme.colors.badgeText
                bgColor:                Theme.colors.badgeCheckout
                visible:                root.repository && root.repository.checkingout
            }
            RepoActionBadge {
                id: theRebaseBadge
                Layout.preferredHeight: theNameLabel.height
                text:                   "Rebase"
                fgColor:                Theme.colors.badgeText
                bgColor:                Theme.colors.badgeRebase
                visible:                root.repository && root.repository.rebasing
            }
            RepoActionBadge {
                id: thePushBadge
                Layout.preferredHeight: theNameLabel.height
                text:                   "Push"
                fgColor:                Theme.colors.badgeText
                bgColor:                Theme.colors.badgePush
                visible:                root.repository && root.repository.pushing
            }
        }
        LabelValueRow {
            id: theBranchRow
            label:      "Branch:"
            width:      theColumn.width
            labelWidth: internal.labelWidth
            BranchCombo {
                id: theBranchCombo
                repository:       root.repository
                font.pointSize:   internal.labelFontSize
                height: 14
            }
        }
        LabelValueRow {
            id: theTrackingRow
            label:      "Tracking:"
            width:      theColumn.width
            labelWidth: internal.labelWidth
            RowLayout {
                Text {
                    id: theTrackingBranchLabel
                    Layout.fillWidth: true
                    color:            "black"
                    text:             root.repository ? root.repository.trackingBranch : ""
                    font.pointSize:   internal.labelFontSize
                    elide:            Text.ElideRight
                }
                Text {
                    id: theTrackingBranchDiffLabel
                    color:                  "black"
                    text:                   "<font color='"+Theme.htmlColor(Theme.colors.branchAhead)+"'>"+ahead+"</font>/<font color='"+Theme.htmlColor(Theme.colors.branchBehind)+"'>"+behind+"</font>"
                    font.pointSize:         internal.labelFontSize
                    font.bold:              true
                    visible:                root.repository && (root.repository.trackingBranchAhead || root.repository.trackingBranchBehind)
                    property string ahead:  root.repository ? "+"+root.repository.trackingBranchAhead : ""
                    property string behind: root.repository ? "-"+root.repository.trackingBranchBehind : ""
                }
            }
        }
        LabelValueRow {
            id: theTrunkRow
            label:      "Trunk:"
            width:      theColumn.width
            labelWidth: internal.labelWidth
            RowLayout {
                Text {
                    id: theTrunkBranchLabel
                    Layout.fillWidth: true
                    color:            "black"
                    text:             root.repository ? root.repository.trunkBranch : ""
                    font.pointSize:   internal.labelFontSize
                    elide:            Text.ElideRight
                }
                Text {
                    id: theTrunkBranchDiffLabel
                    color:                  "black"
                    text:                   "<font color='"+Theme.htmlColor(Theme.colors.branchAhead)+"'>"+ahead+"</font>/<font color='"+Theme.htmlColor(Theme.colors.branchBehind)+"'>"+behind+"</font>"
                    font.pointSize:         internal.labelFontSize
                    font.bold:              true
                    visible:                root.repository && (root.repository.trunkBranchAhead || root.repository.trunkBranchBehind)
                    property string ahead:  root.repository ? "+"+root.repository.trunkBranchAhead : ""
                    property string behind: root.repository ? "-"+root.repository.trunkBranchBehind : ""
                }
            }
        }
        LabelValueRow {
            id: theChangesRow
            label:      "Changes:"
            width:      theColumn.width
            labelWidth: internal.labelWidth
            height:     theChangesText.implicitHeight
            Text {
                id: theChangesText
                font.pointSize: internal.labelFontSize
                font.bold:      internal.hasChanges
                elide:          Text.ElideRight
                text:           internal.changeSummary
                wrapMode:       Text.Wrap
            }
        }
    }

    RepoActionBadge {
        id: theErrorBadge
        anchors.margins: 4
        anchors.right:   parent.right
        anchors.bottom:  parent.bottom
        height:          theNameLabel.height
        fgColor:         Theme.colors.badgeText
        bgColor:         Theme.colors.badgeError
        MouseArea {
            anchors.fill: parent
            onClicked: {
                root.clicked()
                root.showOutput()
                theErrorBadge.visible = false
            }
        }
    }
}
