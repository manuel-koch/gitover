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
import QtQuick.Controls 2.5
import Gitover 1.0
import "."

Item {
    id: root

    property Repo repository: null
    property var commits:     repository != null ? repository.commits : null
    property string selectedCommit: commits != null && theList.currentIndex != -1 ? commits[theList.currentIndex] : ""

    ListView {
        id: theList
        anchors.fill:     parent
        anchors.margins:  2
        clip:             true
        snapMode:         ListView.NoSnap
        boundsBehavior:   Flickable.StopAtBounds
        focus:            true

        model: root.commits

        onModelChanged: {
            theList.currentIndex = -1
        }

        onCountChanged: {
            theList.currentIndex = -1
        }

        highlightFollowsCurrentItem: true
        highlightMoveDuration:       0
        highlightResizeDuration:     0
        highlight: Rectangle {
            color: Theme.colors.selectedRepoBg
        }

        ScrollBar.vertical: ScrollBar { }

        delegate: Item {
            id: theDelegate
            width:  theList.width
            height: childrenRect.height
            property CommitDetails details: CommitDetails {
                repository: root.repository
                rev:        modelData

                Component.onCompleted: {
                    console.info("CommitDetails for "+rev);
                }
            }
            Column {
                width: parent.width
                RowLayout {
                    id: theCommitRow
                    width:  root.width
                    height: theMsg.height

                    SelectableTextline {
                        id: theRev
                        Layout.leftMargin:     10
                        Layout.preferredWidth: 60
                        text:                  theDelegate.details.shortrev ? theDelegate.details.shortrev : ""
                        font.family:           "courier"
                        font.pointSize:        Theme.fonts.smallPointSize
                    }
                    SelectableTextline {
                        Layout.preferredWidth: 160
                        text:                  theDelegate.details.date ? theDelegate.details.date : ""
                        font.pointSize:        Theme.fonts.smallPointSize
                    }
                    SelectableTextline {
                        Layout.preferredWidth: 120
                        text:                  theDelegate.details.user ? theDelegate.details.user : ""
                        font.pointSize:        Theme.fonts.smallPointSize
                    }
                    SelectableTextline {
                        id: theMsg
                        Layout.fillWidth: true
                        wrapMode:         TextInput.WordWrap
                        text:             theDelegate.details.msg ? theDelegate.details.msg : ""
                        label:            theDelegate.details.tags.map( function(t) { return "<b>"+t+"</b>";} ).join("  ")
                        font.family:      "courier"
                        font.pointSize:   Theme.fonts.smallPointSize
                    }
                }
                // FIXME: This repeater is likely to cause Qt crash when too many changes need to be displayed !
                Repeater {
                    model: details.changes
                    RowLayout {
                        id: theChangeRow
                        width:  root.width
                        height: thePath.height

                        Text {
                            id: theChange
                            Layout.leftMargin:     70 + 160 + 120 + 3*theCommitRow.spacing
                            Layout.preferredWidth: 12
                            text:                  modelData.change
                            font.family:           "courier"
                            font.pointSize:        Theme.fonts.smallPointSize
                            color:                 Theme.changeTypeToColor(text)
                        }
                        SelectableTextline {
                            id: thePath
                            Layout.fillWidth: true
                            text:             modelData.path
                            wrapMode:         TextInput.WrapAnywhere
                            font.family:      "courier"
                            font.pointSize:   Theme.fonts.smallPointSize
                        }
                    }
                }
            }
            MouseArea {
                anchors.fill:            theDelegate
                acceptedButtons:         Qt.LeftButton | Qt.RightButton
                propagateComposedEvents: true
                onPressed: {
                    mouse.accepted = false // allow mouse handler within the delegate to react too
                    theList.currentIndex = index
                }
            }
        }
    }
}
