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

Item {
    id: root

    function openDialog() {
        closeDialog()
        theLoader.sourceComponent = theDlgComponent
    }

    function closeDialog() {
        if( theLoader.item ) {
            theLoader.item.close()
            theLoader.sourceComponent = null
        }
    }

    property string title
    property string subTitle
    property string text

    signal ok()
    signal canceled()

    // Using plain Dialog seems to raise strange errors/exceptions when application terminates
    // As a workaround we create a Dialog instance when needed and destroy it afterwards.
    Component {
        id: theDlgComponent
        Dialog {
            id: theInputDialog
            modality:        Qt.WindowModal
            standardButtons: StandardButton.Ok | StandardButton.Cancel
            title:           root.title
            onVisibleChanged: {
                if( visible )
                    theAnswer.focus = true
            }
            onAccepted: {
                root.text = theAnswer.text
                root.ok()
                root.closeDialog()
            }
            onRejected: {
                root.canceled()
                root.closeDialog()
            }
            ColumnLayout {
                id: column
                width: parent ? parent.width : 100
                Label {
                    text:                root.subTitle
                    Layout.fillWidth:    true
                    Layout.maximumWidth: 400
                    wrapMode:            Text.WordWrap
                }
                TextField {
                    id: theAnswer
                    Layout.fillWidth:    true
                    Layout.minimumWidth: 400
                    text:                root.text
                }
            }
        }
    }

    Loader {
        id: theLoader
        sourceComponent: null
        onItemChanged: {
            if( item )
                item.open()
        }
    }
}
