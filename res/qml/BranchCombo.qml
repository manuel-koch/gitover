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

Item {
    id: root

    property font font

    property Repo repository: null

    Connections {
        target: repository
        onBranchChanged:   theCombo.useBranches(repository.branch,repository.branches)
        onBranchesChanged: theCombo.useBranches(repository.branch,repository.branches)
    }

    ComboBox {
        id: theCombo
        anchors.fill: parent

        style: ComboBoxStyle {
            font: root.font
        }

        onActivated: {
            if( index > 1 )
                repository.triggerCheckoutBranch( textAt(index) )
            currentIndex = 0
        }

        function selectBranch(branch) {
            theCombo.currentIndex = theCombo.find(branch)
        }

        function useBranches(branch,branches) {
            var b = [branch]
            for( var i=0; i<branches.length; i++ ) {
                if( b.indexOf(branches[i]) == -1 ) {
                    if( b.length == 1 )
                        b.push("---")
                    b.push( branches[i] )
                }
            }
            theCombo.model = b
            theCombo.currentIndex = 0
        }

        Component.onCompleted: useBranches(repository.branch,repository.branches)
    }

}
