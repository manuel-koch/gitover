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
        theLoader.sourceComponent = theDlgComponent
    }

    function closeDialog() {
        if( theLoader.item ) {
            theLoader.item.close()
            theLoader.sourceComponent = null
        }
    }

    // Using plain MessageDialog seems to raise strange errors/exceptions when application terminates
    // As a workaround we create a MessageDialog instance when needed and destroy it afterwards.
    Component {
        id: theDlgComponent
        MessageDialog {
            id: theAboutDialog
            title: "About"
            text: "Gitover " + globalVersion + "\nBuild from git commit " + globalCommitSha
            onAccepted: root.closeDialog()
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
