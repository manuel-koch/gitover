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

    property string title

    signal selected(url url)
    signal aborted()

    function openDialog() {
        theLoader.sourceComponent = theDlgComponent
    }

    function closeDialog() {
        if( theLoader.item ) {
            theLoader.item.close()
            theLoader.sourceComponent = null
        }
    }

    // Using plain FileDialog seems to raise strange errors/exceptions when application terminates
    // As a workaround we create a FileDialog instance when needed and destroy it afterwards.
    Component {
        id: theDlgComponent
        FileDialog {
            id: theDialog
            title:          root.title
            folder:         shortcuts.home
            selectFolder:   true
            selectExisting: true
            onAccepted: {
                root.selected( theDialog.fileUrls[0] )
                root.closeDialog()
            }
            onRejected: {
                root.aborted()
                root.closeDialog()
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
