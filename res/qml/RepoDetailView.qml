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

    radius:        4
    border.width:  1
    border.color:  "silver"
    color:         "transparent"
    clip:          true

    property Repo repository: null

    Flickable {
        anchors.fill:    root
        anchors.margins: 2
        contentWidth:    width
        contentHeight:   theColumns.implicitHeight

        ColumnLayout {
            id: theColumns
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
                text:             nofModified + " modified files:"
                font.bold:        true
                visible:          nofModified
                property int nofModified: repository != null ? repository.modified.length : 0
            }
            Repeater {
                Layout.fillWidth:  true
                model:             repository != null ? repository.modified : null
                Text {
                    text:           modelData
                    leftPadding:    10
                    font.pointSize: 10
                }
            }
            Text {
                Layout.fillWidth: true
                text:             nofDeleted + " deleted files:"
                font.bold:        true
                visible:          nofDeleted
                property int nofDeleted: repository != null ? repository.deleted.length : 0
            }
            Repeater {
                Layout.fillWidth: true
                model:            repository != null ? repository.deleted : null
                Text {
                    text:           modelData
                    leftPadding:    10
                    font.pointSize: 10
                }
            }
            Text {
                Layout.fillWidth: true
                text:             nofUntracked + " untracked files:"
                font.bold:        true
                visible:          nofUntracked
                property int nofUntracked: repository != null ? repository.untracked.length : 0
            }
            Repeater {
                Layout.fillWidth: true
                model:            repository != null ? repository.untracked : null
                Text {
                    text:           modelData
                    leftPadding:    10
                    font.pointSize: 10
                }
            }
        }
    }
}
