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
import QtQuick.Controls 2.1
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
        onClicked: root.clicked()
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

        Text {
            id: theNameLabel
            width:          theColumn.width
            color:          root.repository.refreshing ? "red" : "black"
            text:           root.repository ? root.repository.name : ""
            elide:          Text.ElideRight
            font.bold:      true
            font.pointSize: internal.titleFontSize
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
            }
        }
        LabelValueRow {
            id: theTrackingRow
            label:      "Tracking:"
            width:      theColumn.width
            labelWidth: internal.labelWidth
            Text {
                id: theTrackingBranchLabel
                color:                  "black"
                text:                   ( diff ? ("<b><font color='green'>"+ahead+"</font>/<font color='red'>"+behind+"</font></b> ") : "") +
                                        ( root.repository ? root.repository.trackingBranch : "" )
                font.pointSize:         internal.labelFontSize
                property bool diff:     root.repository && (root.repository.trackingBranchAhead || root.repository.trackingBranchBehind)
                property string ahead:  root.repository ? "+"+root.repository.trackingBranchAhead : ""
                property string behind: root.repository ? "-"+root.repository.trackingBranchBehind : ""
            }
        }
        LabelValueRow {
            id: theTrunkRow
            label:      "Trunk:"
            width:      theColumn.width
            labelWidth: internal.labelWidth
            Text {
                id: theTrunkBranchLabel
                color:                  "black"
                text:                   ( diff ? ("<b><font color='green'>"+ahead+"</font>/<font color='red'>"+behind+"</font></b> ") : "") +
                                        ( root.repository ? root.repository.trunkBranch : "" )
                font.pointSize:         internal.labelFontSize
                property bool diff:     root.repository && (root.repository.trunkBranchAhead || root.repository.trunkBranchBehind)
                property string ahead:  root.repository ? "+"+root.repository.trunkBranchAhead : ""
                property string behind: root.repository ? "-"+root.repository.trunkBranchBehind : ""
            }
        }
    }
}
