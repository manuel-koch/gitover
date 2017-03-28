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

    height:        theColumn.implicitHeight + 2*radius
    radius:        4
    border.width:  1
    border.color:  "silver"
    color:         "transparent"
    clip:          true

    property Repo repository: null

    signal clicked()

    Component.onCompleted: console.debug(repository,repository.name)

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
            Image {
                id: theStatusIcon
                Layout.preferredWidth:  theNameLabel.height
                Layout.preferredHeight: theNameLabel.height
                fillMode:               Image.Stretch
                source:                 "../status.png"
                visible:                root.repository && root.repository.updating
            }
            Image {
                id: theFetchIcon
                Layout.preferredWidth:  theNameLabel.height
                Layout.preferredHeight: theNameLabel.height
                fillMode:               Image.Stretch
                source:                 "../fetch.png"
                visible:                root.repository && root.repository.fetching
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
                    text:                   "<font color='green'>"+ahead+"</font>/<font color='red'>"+behind+"</font>"
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
                    text:                   "<font color='green'>"+ahead+"</font>/<font color='red'>"+behind+"</font>"
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
                elide:          Text.ElideRight
                text:           getChangesNums(modified,deleted,untracked,conflicts,staged)
                wrapMode:       Text.Wrap
                /*
                FIXME: Popup causes problems when bundling/freezing with PyInstaller !?
                MouseArea {
                    id: theChangesMouseArea
                    anchors.fill: parent
                    onClicked: {
                        if( theChangesText.hasChanges ) {
                            popupText.text = theChangesText.getChanges()
                            theChangesText.findPopupPos()
                            popup.open()
                        }
                    }
                }

                function findPopupPos(item) {
                    var rootitem = theChangesText
                    while( rootitem.parent ) { rootitem = rootitem.parent }
                    var pt = theChangesText.mapToItem(rootitem,popup.width,popup.height)
                    popup.x = rootitem.width < pt.x ? rootitem.width - pt.x : 0
                    popup.y = rootitem.height < pt.y ? rootitem.height - pt.y : 0
                }

                Popup {
                    id: popup
                    modal:       true
                    focus:       true
                    padding:     4
                    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
                    Text {
                        id: popupText
                        text: "foo"
                        font.pointSize: internal.labelFontSize
                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: popup.close()
                            onContainsMouseChanged: {
                                if( !containsMouse )
                                    popup.close()
                            }
                        }
                    }
                }
                */

                property bool hasChanges: untracked || modified || deleted || conflicts || staged
                property int untracked: root.repository ? root.repository.untracked.length : 0
                property int modified: root.repository ? root.repository.modified.length : 0
                property int deleted: root.repository ? root.repository.deleted.length : 0
                property int conflicts: root.repository ? root.repository.conflicts.length : 0
                property int staged: root.repository ? root.repository.staged.length : 0
                property string tooltipText: ""

                function getChangesNums(m,d,u,c,s) {
                    var t = []
                    if( s )
                        t.push("<font color='#C1036E'>"+s+"-S</font>")
                    if( c )
                        t.push("<font color='#950000'>"+c+"-C</font>")
                    if( m )
                        t.push("<font color='#007272'>"+m+"-M</font>")
                    if( d )
                        t.push("<font color='#F00303'>"+d+"-D</font>")
                    if( u )
                        t.push("<font color='#F06E03'>"+u+"-U</font>")
                    if( !m && !d && !u && !c && !s)
                        t.push("<font color='#03C003'>up-to-date</font>")
                    return t.join(", ")
                }

                function getChanges() {
                    var t = []
                    appendToArray(t,root.repository.staged,"staged")
                    appendToArray(t,root.repository.conflicts,"conflicts")
                    appendToArray(t,root.repository.modified,"modified")
                    appendToArray(t,root.repository.deleted,"deleted")
                    appendToArray(t,root.repository.untracked,"untracked")
                    return t.join("<br>")
                }

                function appendToArray(target,source,title) {
                    if( source.length ){
                        target.push("<b>"+title+":</b>")
                        for(var i=0;i<source.length;i++)
                            t.push("&nbsp;&nbsp;"+source[i])
                    }
                }
            }
        }
    }
}
