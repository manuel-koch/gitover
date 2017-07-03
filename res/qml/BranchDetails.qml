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
import QtQuick.Controls.Styles 1.4
import Gitover 1.0
import "."

Item {
    id: root

    implicitHeight: childrenRect.height

    property Repo repository: null
    property string title: ""
    property var commits: null

    Text {
        id: theTitle
        width:     parent.width
        height:    implicitHeight
        text:      root.title
        font.bold: true
    }

    Column {
        anchors.top:       theTitle.bottom
        anchors.topMargin: 4
        width:             parent.width
        spacing:           4

        Repeater {
            model: commits

            Column {
                width: parent.width

                property var details: root.repository.commit(modelData)

                RowLayout {
                    id: theCommitRow
                    width:  root.width
                    height: theRev.height

                    SelectableTextline {
                        id: theRev
                        Layout.leftMargin:     10
                        Layout.preferredWidth: 60
                        text:                  details.rev
                        font.family:           "courier"
                        font.pointSize:        Theme.fonts.smallPointSize
                    }
                    SelectableTextline {
                        Layout.preferredWidth: 120
                        text:                  details.user
                        font.pointSize:        Theme.fonts.smallPointSize
                    }
                    SelectableTextline {
                        Layout.fillWidth: true
                        text:             details.msg
                        font.family:      "courier"
                        font.pointSize:   Theme.fonts.smallPointSize
                    }
                }
                Repeater {
                    model: details.changes
                    RowLayout {
                        id: theChangeRow
                        width:  root.width
                        height: theChange.height

                        Text {
                            id: theChange
                            Layout.leftMargin:     190 + 2*theCommitRow.spacing
                            Layout.preferredWidth: 12
                            text:                  modelData.change
                            font.family:           "courier"
                            font.pointSize:        Theme.fonts.smallPointSize
                            color:                 Theme.changeTypeToColor(text)
                        }
                        SelectableTextline {
                            Layout.fillWidth: true
                            text:             modelData.path
                            font.family:      "courier"
                            font.pointSize:   Theme.fonts.smallPointSize
                        }
                    }
                }
            }
        }
    }
}
